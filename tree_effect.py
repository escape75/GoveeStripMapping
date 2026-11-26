"""
A vertical bar circling the mapped tree, slowly changing color. The rest of the tree is off.

Put this file next to govee_strip.py and your tree_3d_multi.json, then (from that folder):

  python tree_effect.py tree_3d_multi.json                       # strips and addresses come from the file
  python tree_effect.py tree_3d_multi.json --width 20 --turns 0.4
  python tree_effect.py tree_3d_multi.json --dry                 # no Bluetooth, just print stats
  python govee_strip.py --scan                                    # lists names AND addresses
  python tree_effect.py tree_3d_multi.json --address AA:BB:CC:DD:EE:01 --address AA:BB:CC:DD:EE:02

Ctrl+C turns the lights off and disconnects. Quit the Govee app first.
"""
import argparse
import asyncio
import colorsys
import json
import math
import time


def load_strands(path):
    """[(strand number, strip name, {index: (x, y, z)}, address), ...] in the order of the file"""
    data = json.load(open(path, encoding="utf-8"))
    return [(st.get("strand"), str(st.get("strip") or ""),
             {l["index"]: (l["x"], l["y"], l["z"]) for l in st["leds"]}, str(st.get("address") or "")) for st in data["strands"]]


def is_mac(a):
    return len(a) == 17 and a.count(":") == 5


def bar_frame(pts, t, args):
    """Tree off; a vertical wedge sweeps around the tree and slowly changes color."""
    centre = (t * args.turns * 2 * math.pi) % (2 * math.pi)
    half_w = math.radians(args.width) / 2
    h = round(((t * 0.08) % 1.0) * args.hues) / args.hues
    r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
    full = (int(r * 255), int(g * 255), int(b * 255))
    dim = (full[0] // 4, full[1] // 4, full[2] // 4)
    out = {}
    for key, (x, y, z) in pts.items():
        d = abs((math.atan2(z, x) - centre + math.pi) % (2 * math.pi) - math.pi)
        if d < half_w * 0.6:
            out[key] = full
        elif d < half_w:
            out[key] = dim                                        # soft edge
    return out


async def run(args):
    from govee_strip import GoveeStrip
    strands = load_strands(args.json)
    addrs = args.address or []
    saved = [st[3] for st in strands]
    if not addrs and all(is_mac(a) for a in saved):
        addrs = saved                                             # the scan saved which strip each strand is
        print("Using the strip addresses saved in the file:", ", ".join(f"{st[1] or '?'} {st[3]}" for st in strands))
    if len(addrs) >= 2:                                           # several strips: address k drives strand k of the file
        if len(addrs) > len(strands):                             # e.g. a one-strip file: reuse the last map for the extra strips
            print(f"Note: the file has {len(strands)} strand(s) but {len(addrs)} addresses were given; the last map is "
                  "used for the extra strip(s), so they show the same pattern in the same place (fine for a test).")
            strands = strands + [strands[-1]] * (len(addrs) - len(strands))
        chosen = list(zip(addrs, strands))
    else:
        st = next((x for x in strands if x[0] == args.strand), strands[0])
        chosen = [(addrs[0] if addrs else (st[3] if is_mac(st[3]) else None), st)]
    # all strips share one coordinate system, so the bar runs straight across them
    pts = {(k, i): xyz for k, (_, (_, _, p, _)) in enumerate(chosen) for i, xyz in p.items()}
    print(f"{len(chosen)} strip(s), {len(pts)} mapped LEDs")

    if args.dry:
        strips = [GoveeStrip() for _ in chosen]
        for st in strips:
            st.clear()
        for (k, i), c in bar_frame(pts, 1.0, args).items():
            strips[k].set([i], c)
        for k, st in enumerate(strips):
            print(f"strip {k + 1} frame:", len(st.leds), "lit,", len(st.packet()), "bytes")
        return

    strips = []
    try:
        for addr, (num, sname, _, _) in chosen:
            name = args.name or sname or "6870"
            print(f"Connecting to strand {num}: " + (f"address {addr}" if addr else f"name containing '{name}'"))
            st = GoveeStrip(name, addr)
            await st.connect()
            st.set_brightness(args.brightness)
            strips.append(st)
        print("Connected. Ctrl+C to stop.")
        t0 = time.time()
        frames, tick = 0, time.time()
        while True:
            now = time.time()
            for st in strips:
                st.clear()
            for (k, i), c in bar_frame(pts, now - t0, args).items():
                strips[k].set([i], c)
            await asyncio.gather(*[st.show(wait=False) for st in strips])
            frames += 1
            if time.time() - tick >= 3:
                print(f"{frames / (time.time() - tick):.1f} frames/s")
                frames, tick = 0, time.time()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        for st in strips:
            st.clear()
            try:
                st._pending = 0                          # forget unanswered frames, then send "all off"
                await st.show()
            except Exception as e:
                print("lights off may not have been confirmed:", e)
            try:
                await st.disconnect()
            except Exception:
                pass


def main():
    ap = argparse.ArgumentParser(description="Vertical bar circling a mapped tree.")
    ap.add_argument("json", help="the exported tree_3d_multi.json")
    ap.add_argument("--strand", type=int, default=1, help="which strand of the file when only one strip is used (default 1)")
    ap.add_argument("--width", type=float, default=30, help="bar width in degrees around the tree")
    ap.add_argument("--turns", type=float, default=0.25, help="bar speed in turns per second")
    ap.add_argument("--hues", type=int, default=8, help="color steps (fewer = smaller frames)")
    ap.add_argument("--brightness", type=int, default=100)
    ap.add_argument("--name", help="part of the Bluetooth name (default: the strip name saved in the JSON)")
    ap.add_argument("--address", action="append", help="Bluetooth address; give it twice for two strips")
    ap.add_argument("--dry", action="store_true", help="no Bluetooth; print packet size")
    args = ap.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
