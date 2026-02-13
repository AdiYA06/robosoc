ls /dev/cu.usbmodem*
ipconfig getifaddr en0
python3 web_controller/pi_control_server.py --serial-port /dev/cu.usbmodem2101 --baud 115200 --serial-required