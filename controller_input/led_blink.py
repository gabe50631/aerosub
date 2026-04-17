import time

LED_PATH = "/sys/class/leds/work/brightness"
TRIGGER_PATH = "/sys/class/leds/work/trigger"

# disable default behavior
try:
    with open(TRIGGER_PATH, "w") as f:
        f.write("none")
except FileNotFoundError:
    pass  # some images don't have trigger

delay = 0.1  # 5 Hz (0.1s on, 0.1s off)

try:
    while True:
        with open(LED_PATH, "w") as f:
            f.write("1")
        time.sleep(delay)

        with open(LED_PATH, "w") as f:
            f.write("0")
        time.sleep(delay)

except KeyboardInterrupt:
    with open(LED_PATH, "w") as f:
        f.write("0")