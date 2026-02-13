import ota
import machine
import network

# github repository access and files to update
ota = ota.ota(
  user="gitzenlab",
  repo="eye",
  branch="main",
  working_dir="eye",
  files = ["boot.py", "main.py", "dotmatrix.py"]
)

try:
    ota.wificonnect()
    if ota.update():
        print("rebooting...")
        machine.reset()
    else:
        # deactivate micropython ap
        ap = network.WLAN(network.AP_IF)
        if ap.active():
            ap.active(False)
except OSError as e:
    print(f"error: {e}")
