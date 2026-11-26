"""
Govee H6870 Mapping Server
Run:    python.exe server.py
Phone:  https://<PC-IP>:5000  (same Wi-Fi)
"""
import asyncio
import json
import socket
import threading
import time
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, redirect

from govee_strip import GoveeStrip

BASE_DIR   = Path(__file__).parent
MAPS_DIR   = BASE_DIR / "maps"
STATIC_DIR = BASE_DIR / "static"
CAPTURES_DIR = BASE_DIR / "captures"
MAPS_DIR.mkdir(exist_ok=True)
CAPTURES_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=None)


# ---------------------------------------------------------------------------
# BLE worker — owns a GoveeStrip on its own asyncio loop
# One worker per strand, keyed by its MAC address (or the name it was found by)
# ---------------------------------------------------------------------------
class BleWorker:
    def __init__(self):
        self.loop  = asyncio.new_event_loop()
        self.strip = None
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def submit(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    async def connect(self, name=None, address=None):
        if self.strip:
            await self.strip.__aexit__(None, None, None)
        self.strip = GoveeStrip(name=name, address=address, verbose=False)
        await self.strip.__aenter__()

    async def disconnect(self):
        if self.strip:
            await self.strip.__aexit__(None, None, None)
            self.strip = None

    def _need(self):
        if not self.strip:
            raise RuntimeError("Not connected")

    async def identify(self, index, color="ff0000"):
        self._need()
        self.strip.clear()
        self.strip.set(index, color)
        await self.strip.show()

    async def clear(self):
        self._need()
        self.strip.clear()
        await self.strip.show()

    async def chase(self, count=250, color="00ff00", delay=0.05):
        self._need()
        self.strip.clear()
        await self.strip.show()
        for i in range(count):
            if i > 0:
                self.strip.off(i - 1)
            self.strip.set(i, color)
            await self.strip.show()
            await asyncio.sleep(delay)

    async def set_mask(self, on_indices, on_color="ff00ff", bg_color="202020", total=250, groups=None):
        """Light the given indices in on_color, rest in bg_color. groups = [{indices, color}, ...] lights several colors at once."""
        self._need()
        self.strip.clear()
        for g in groups or []:
            for i in g.get("indices", []):
                if 0 <= i < total:
                    self.strip.set(i, g.get("color", on_color))
        
        # Set background color
        if bg_color and bg_color != "000000":
            for i in range(total):
                self.strip.set(i, bg_color)
                
        # Set active color
        for i in on_indices:
            if 0 <= i < total:
                self.strip.set(i, on_color)
                
        await self.strip.show()
        return getattr(self.strip, "last_timing", None)


# One worker per strand, keyed by the strand's MAC address (or the name used to find it).
workers = {}
workers_lock = threading.Lock()
names = {}                       # address -> Bluetooth name, e.g. Govee_H6870_6778
last_device = "default"          # most recently connected strand; used when a request names none


def connect_key(d):
    addr = (d.get("address") or "").strip().upper()
    return addr or (d.get("name") or "").strip() or "default"


def device_key(d):
    return (d.get("device") or "").strip() or last_device


def get_worker(device_id):
    with workers_lock:
        if device_id not in workers:
            workers[device_id] = BleWorker()
        return workers[device_id]


def run(coro, timeout=30):
    # caller ensures the coro goes to the right loop; this helper just waits
    return coro.result(timeout=timeout)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.get("/merge")
def merge_page():
    return send_from_directory(str(STATIC_DIR), "merge.html")


@app.get("/multi")
def multi_page():
    return redirect("/merge")                      # one page handles any number of strips


@app.post("/api/connect")
def api_connect():
    global last_device
    d = request.get_json(force=True)
    device_id = connect_key(d)
    w = get_worker(device_id)
    try:
        w.submit(w.connect(name=d.get("name"), address=d.get("address"))).result(timeout=45)
        # Two strips can share a Bluetooth name, so from here on a strip is identified by the address it really has.
        real = (getattr(w.strip, "found_address", None) or device_id).upper()
        label = getattr(w.strip, "found_name", None) or ""
        with workers_lock:
            other = workers.get(real)
            if other is not None and other is not w and other.strip is not None:
                w.submit(w.disconnect()).result(timeout=10)
                return jsonify(ok=False, error=f"That is the strip {label or real} again, which is already connected. "
                                               "To connect the other one, type its own name (e.g. Govee_H6870_8274) or its address in the dialog."), 409
            if real != device_id:
                workers.pop(device_id, None)
                workers[real] = w
        names[real] = label
        last_device = real
        return jsonify(ok=True, device=real, name=label)
    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500


@app.post("/api/disconnect")
def api_disconnect():
    d = request.get_json(force=True) if request.data else {}
    device_id = device_key(d)
    w = get_worker(device_id)
    try:
        w.submit(w.disconnect()).result(timeout=10)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.post("/api/identify")
def api_identify():
    d = request.get_json(force=True)
    device_id = device_key(d)
    w = get_worker(device_id)
    try:
        w.submit(w.identify(int(d["index"]), d.get("color", "ff0000"))).result(timeout=15)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.post("/api/chase")
def api_chase():
    d = request.get_json(force=True)
    device_id = device_key(d)
    w = get_worker(device_id)
    try:
        w.submit(w.chase(
            count=int(d.get("count", 250)),
            color=d.get("color", "00ff00"),
            delay=float(d.get("delay", 0.05)),
        )).result(timeout=180)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.post("/api/clear")
def api_clear():
    d = request.get_json(force=True) if request.data else {}
    device_id = device_key(d)
    w = get_worker(device_id)
    try:
        w.submit(w.clear()).result(timeout=15)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.post("/api/set_mask")
def api_set_mask():
    """Light only the given indices (on_color), everything else in bg_color. Used by the camera mapper."""
    d = request.get_json(force=True)
    device_id = device_key(d)
    w = get_worker(device_id)
    try:
        timing = w.submit(w.set_mask(
            on_indices=d.get("indices", []),
            on_color=d.get("color", "ff0000"),
            bg_color=d.get("bg_color", "000000"),
            total=int(d.get("total", 250)),
            groups=d.get("groups"),
        )).result(timeout=30)
        return jsonify(ok=True, timing=timing)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


# ---- Map persistence -------------------------------------------------------
def _safe(name):
    return "".join(c for c in name if c.isalnum() or c in "-_") or "layout"


@app.post("/api/maps")
def api_save_map():
    d = request.get_json(force=True)
    name = _safe(d.get("name", "layout"))
    payload = {
        "version": 1,
        "count": len(d["coordinates"]),
        "shape": d.get("shape", "path"),
        "coordinates": d["coordinates"],
    }
    (MAPS_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2))
    return jsonify(ok=True, filename=f"{name}.json")


@app.get("/api/maps")
def api_list_maps():
    return jsonify(ok=True, maps=sorted(p.name for p in MAPS_DIR.glob("*.json")))


@app.get("/api/maps/<path:name>")
def api_get_map(name):
    p = MAPS_DIR / name
    if not p.is_file() or p.parent != MAPS_DIR:
        return jsonify(ok=False, error="not found"), 404
    return jsonify(ok=True, data=json.loads(p.read_text()))


# ---- Camera captures (one per phone position; merged on /merge) -----------
@app.post("/api/captures")
def api_save_capture():
    d = request.get_json(force=True)
    strips = d.get("strips")                    # several strips scanned together keep their results inside each strip
    ok = isinstance(d.get("results"), list) or (isinstance(strips, list) and strips and all(isinstance(x.get("results"), list) for x in strips))
    if not ok:
        return jsonify(ok=False, error="no results array"), 400
    name = _safe(d.pop("name", "") or f"capture-{int(time.time())}")
    (CAPTURES_DIR / f"{name}.json").write_text(json.dumps(d))       # the debug info (report, settings, camera) stays inside the file
    return jsonify(ok=True, filename=f"{name}.json")


@app.get("/api/captures")
def api_list_captures():
    out = []
    for p in sorted(CAPTURES_DIR.glob("*.json"), key=lambda q: q.stat().st_mtime):
        try:
            j = json.loads(p.read_text())
            strips = j.get("strips")                         # several strips scanned together (version 5)
            if strips:
                dev = "+".join(str(x.get("strip") or "?") for x in strips)
                seen = sum(1 for x in strips for r in x.get("results", []) if r.get("status") == "ok")
                out.append(dict(name=p.name, time=p.stat().st_mtime, device=dev, count=j.get("count"), seen=seen,
                                strips=[x.get("stripName") or x.get("strip") for x in strips]))
            else:
                res = j.get("results", [])
                out.append(dict(name=p.name, time=p.stat().st_mtime, device=j.get("device"),
                                count=j.get("count"), seen=sum(1 for r in res if r.get("status") == "ok")))
        except Exception:
            pass
    return jsonify(ok=True, captures=out)


@app.get("/api/captures/<path:name>")
def api_get_capture(name):
    p = CAPTURES_DIR / name
    if not p.is_file() or p.parent != CAPTURES_DIR or p.suffix != ".json":
        return jsonify(ok=False, error="not found"), 404
    return jsonify(ok=True, data=json.loads(p.read_text()))


@app.delete("/api/captures/<path:name>")
def api_delete_capture(name):
    p = CAPTURES_DIR / name
    if p.is_file() and p.parent == CAPTURES_DIR and p.suffix == ".json":
        p.unlink()
        return jsonify(ok=True)
    return jsonify(ok=False, error="not found"), 404


@app.get("/api/info")
def api_info():
    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    connected = {k: (w.strip is not None) for k, w in workers.items()}
    return jsonify(ok=True, ip=ip, connected=connected, last=last_device, names=names, captures=True)


if __name__ == "__main__":
    print("=" * 60)
    print("Govee H6870 mapping server")
    print("Open on your phone (same Wi-Fi):")
    print("   https://<PC-IP>:5000")
    print("Find PC IP with:  ipconfig")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, threaded=True, ssl_context="adhoc")