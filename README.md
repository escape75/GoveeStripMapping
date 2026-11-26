<pre>

The goal of this project was to investigate the feasibility of a 3D mapping solution
capable of using camera vision to identify and map the individual LED positions
of two or more Govee light strips wrapped around a Christmas tree.
   
   The sample.mp4 video shows the result obtained with 7 captures.
   
   
QUICK START (5 steps)
----------------------
1. Extract portable-python (python-3.13.8-embed-amd64) to your workspace folder
2. Edit python313._pth to enable site module:

   Open file: python313._pth

   Uncomment the "import site" line by removing the # before it:

     python313.zip
     .
     import site  &lt;- remove the # symbol

3. Install pip if needed (minimal portable Python may not have it):

   curl -o get-pip.py https://bootstrap.pypa.io/get-pip.py
   python.exe get-pip.py

4. Install dependencies from requirements file (recommended):

   Create a `requirements.txt` file with the following content and run:
   ```text
   flask==2.3.3
   bleak&gt;=1.0
   cryptography&gt;=42.0
   prompt_toolkit
   ```
   python.exe -m pip install -r requirements.txt

5. Copy application files from another folder if needed (optional):

   If you have an existing installation with these files, copy them to your workspace:
   
   • govee_strip.py    ← BLE protocol library
   • server.py         ← Web server application  
   • tree_effect.py    ← Tree effects demo
   • static/index.html ← Camera mapper UI
   • static/merge.html  ← 3D merge tool

   Then you're ready to use! (see USAGE MODES below for examples)

================================================================================
COMMAND-LINE USAGE REFERENCE
================================================================================

govee_strip.py - Direct BLE control
------------------------------------
Usage:  python.exe govee_strip.py leds [options]

Options:
  --scan             List nearby BLE devices (Govee H6870/H6871)
  --name &lt;string&gt;    Device name suffix to match (default: "6871")
  --address &lt;addr&gt;   Connect using Bluetooth address instead of name
  --on &lt;leds&gt;        Light specific LEDs (e.g. "0-9,100", "217", "5-10")
  --color &lt;rgb&gt;      Color for --on (RRGGBB or names: red, green, blue)
  --fill &lt;color&gt;     Set whole strip to one color
  --power on|off     Power the strip on or off
  --brightness &lt;n&gt;   Brightness 1-100
  --background &lt;c&gt;   Background color (RRGGBB or "off", default: off)
  --effect &lt;e&gt;       Effect mode: twinkle, fade, breathe, static, hex code
  --speed &lt;n&gt;        Effect speed 0-100
  -v, --verbose      Print decrypted BLE traffic

Example commands:
  python.exe govee_strip.py leds --scan
  python.exe govee_strip.py leds --on 0-249 --color ff00ff --fill
  python.exe govee_strip.py leds --on 5-10,20-30 --color 00ff00,0000ff

tree_effect.py - Vertical bar effect on mapped 3D tree
-----------------------------------------------
Usage:  python.exe tree_effect.py &lt;tree_3d_multi.json&gt; [options]

Options:
  --strand &lt;n&gt;       Which strand in JSON (default: 1)
  --base &lt;b&gt;         Base color/rainbow/spin (default: "rainbow")
  --width &lt;deg&gt;      Bar width in degrees around the tree (default: 30)
  --turns &lt;t&gt;        Bar speed in turns/sec (default: 0.25)
  --hues &lt;n&gt;         Rainbow color steps, fewer = faster frames (default: 8)
  --brightness &lt;n&gt;   LED brightness 1-100 (default: 100)
  --seed &lt;n&gt;         Random seed for reproducible animation
  --name &lt;string&gt;    Device name suffix (uses address from JSON if not given)
  --address &lt;addr&gt;   Bluetooth address; give it twice for two strips
  --dry              Dry run: print stats without touching LEDs

Example commands:
  python.exe tree_effect.py tree_3d_multi.json
  python.exe tree_effect.py tree_3d_multi.json --base red
  python.exe tree_effect.py tree_3d_multi.json --name 6870 --address AA:BB:CC:DD:EE:FF

server.py - Web server for camera mapping & animation playback
--------------------------------------------------------------
Usage:  python.exe server.py [optional args]

Options: None (runs with defaults)

Defaults:
  • Host: 0.0.0.0 (all interfaces)
  • Port: 5000
  • SSL: auto-generated self-signed certificate

Example:
  python.exe server.py
  # Access from phone on same Wi-Fi: https://&lt;PC-IP&gt;:5000

================================================================================
USAGE MODES (Choose One After Installation)
================================================================================

MODE A - Direct CLI Control (Quick & Simple)
  python.exe govee_strip.py leds --scan          # Find device
  python.exe govee_strip.py leds --on 0-249      # Turn on all LEDs
  python.exe govee_strip.py leds --fill ff00ff   # Magenta

MODE B - Tree Effect Demo
  python.exe tree_effect.py tree_3d_multi.json   # Vertical bar circling tree
  python.exe tree_effect.py tree_3d_multi.json --base red

MODE C - Web Server (Camera Mapping & Remote Control)
  python.exe server.py                            # Start on port 5000
  # Open https://&lt;PC-IP&gt;:5000 on phone for camera mapping

================================================================================
POST-INSTALLATION CHECKLIST
================================================================================

[ ] Verify Python:           python.exe --version
[ ] Test pip is available:   python.exe -m pip --version
[ ] Install packages:        python.exe -m pip install flask bleak cryptography prompt_toolkit
[ ] Edit python313._pth:     Uncomment "import site" line if missing
[ ] Copy app files (step 5): See QUICK START step 5 for file list
[ ] Test imports:            python.exe -c "from govee_strip import GoveeStrip"
[ ] Test server:             python.exe server.py  (open https://localhost:5000 in browser)

================================================================================
TROUBLESHOOTING
================================================================================

NO MODULE NAMED PIP:
  • Download and run get-pip.py:
    curl -o get-pip.py https://bootstrap.pypa.io/get-pip.py
    python.exe get-pip.py
  
  • Or try ensurepip if available:
    python.exe -m ensurepip --default-pip

BLE CONNECTION FAILS:
  • Close Govee app first (only one BLE client allowed)
  • Ensure Bluetooth is enabled on PC
  • Check system permissions: On modern Windows and macOS systems, ensure that the terminal or command prompt running this script has explicit Bluetooth/Local Host access granted in your OS privacy settings.
  • Verify device address/name matches expected format

PORTABLE PYTHON ERRORS:
  • "ModuleNotFoundError": Run pip install [missing-module]
  • Import errors from govee_strip.py: Ensure cryptography installed

WEB SERVER NOT STARTING:
  • Port 5000 in use? Kill other Flask processes or change port in server.py
  • SSL warning on first run: Browser will warn but it's safe (self-signed cert)

CAMERA NOT WORKING:
  • Grant camera permission to browser when prompted
  • iOS requires HTTPS or localhost (localhost works fine)
  • Check site permissions: Settings → Safari (or Chrome) → Privacy → Website Data

================================================================================
FILE STRUCTURE AFTER INSTALLATION
================================================================================

python-3.13.8-embed-amd64/
├── Lib/site-packages/     ← Installed packages (flask, bleak, cryptography, prompt_toolkit)
├── Scripts/               ← pip.exe, flask.exe
├── maps/                  ← [Generated during mapping sessions]
├── captures/              ← [Generated during mapping sessions]
├── static/index.html      ← Camera mapper UI
├── static/merge.html      ← 3D merge tool
├── govee_strip.py         ← BLE protocol library (CLI usage above)
├── server.py              ← Web server (no CLI args, uses defaults)
├── tree_effect.py         ← Tree effects demo (vertical bar effect)
├── python313._pth        ← Enable site module: uncomment "import site" line
└── tree_3d_multi.json     ← [Generated from mapping sessions]

================================================================================
HARDWARE REQUIREMENTS
================================================================================

Bluetooth LE (Required for all modes):
  • Windows 10/11 with Bluetooth adapter (most laptops have built-in)
  • macOS CoreBluetooth (automatic, no setup needed)
  • Linux BlueZ/bluetoothctl

Camera (Optional, for visual mapping mode):
  • Phone camera (required for LED position capture)
  • PC webcam (optional preview/debugging in browser)

Browser requirements (for web server + mapping UI):
  • Chrome/Chromium 80+ recommended
  • Firefox 75+, Safari 13.1+, Edge 80+ supported
  • Must support getUserMedia API (camera), Fetch API, Canvas rendering

================================================================================
END OF INSTALLATION GUIDE
================================================================================

</pre>
