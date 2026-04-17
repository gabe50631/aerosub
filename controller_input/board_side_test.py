import socket
import time

LED_PATH = "/sys/class/leds/work/brightness"
TRIGGER_PATH = "/sys/class/leds/work/trigger"

# disable default behavior
try:
    with open(TRIGGER_PATH, "w") as f:
        f.write("none")
except FileNotFoundError:
    pass

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 5005))
sock.setblocking(False)  # IMPORTANT

delay = 0.1
last_toggle = time.time()
led_state = 0

while True:
    # 🔹 Read ALL pending packets (flush backlog)
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            value = float(data.decode())

            # map input → delay
            delay = 0.05 + (1 - value) * 0.5

        except BlockingIOError:
            break  # no more packets

    # 🔹 Non-blocking timing
    now = time.time()
    if now - last_toggle >= delay:
        led_state ^= 1  # toggle 0/1

        with open(LED_PATH, "w") as f:
            f.write("1" if led_state else "0")

        last_toggle = now