from periphery import GPIO
import struct
import time

LED_PIN = 52
EVENT_DEVICE = "/dev/input/event0"

# Setup LED
led = GPIO(LED_PIN, "out")

# Open input device
dev = open(EVENT_DEVICE, "rb")

print("Reading from /dev/input/event0")

BLINK_DELAY = 0.3
led_state = False
last_blink_time = time.time()

try:
    while True:
        data = dev.read(16)  # input_event = 16 bytes

        if data:
            tv_sec, tv_usec, ev_type, code, value = struct.unpack('llHHI', data)

            # EV_ABS = 3 (analog axes)
            if ev_type == 3:
                print(f"Code: {code}, Value: {value}")

                current_time = time.time()

                # 👇 FIND YOUR AXIS HERE FIRST
                if code == 5:   # <-- may need to change

                    # Normalize (typical range 0–65535 or 0–1023)
                    norm = (value - 32768) / 32768.0

                    print(f"Axis approx: {norm:.3f}")

                    # FORWARD → BLINK
                    if norm < -0.5:
                        if current_time - last_blink_time > BLINK_DELAY:
                            led_state = not led_state
                            led.write(led_state)
                            last_blink_time = current_time

                    # BACKWARD → ON
                    elif norm > 0.5:
                        led.write(True)

                    # NEUTRAL → OFF
                    else:
                        led.write(False)

except KeyboardInterrupt:
    print("\nStopped")

finally:
    led.write(False)
    led.close()
    dev.close()