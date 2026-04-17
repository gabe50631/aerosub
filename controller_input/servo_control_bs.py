import time
import os
import socket

# Configuration
PWM_PATH = "/sys/class/pwm/pwmchip9/pwm0"
PERIOD = 20000000  # 20ms (50Hz)
MIN_PULSE = 1000000
MAX_PULSE = 2000000

# UDP setup
PORT = 5005

def write_pwm(file, value):
    try:
        with open(f"{PWM_PATH}/{file}", "w") as f:
            f.write(str(value))
    except OSError as e:
        print(f"Error writing {value} to {file}: {e}")

def setup():
    if not os.path.exists(PWM_PATH):
        with open("/sys/class/pwm/pwmchip9/export", "w") as f:
            f.write("0")
        time.sleep(0.5)

    write_pwm("enable", "0")
    write_pwm("duty_cycle", "0")
    write_pwm("period", PERIOD)
    write_pwm("duty_cycle", 1500000)  # safe center
    write_pwm("enable", "1")

    print(">>> Servo ready")

def set_angle(angle):
    angle = max(15, min(180, angle))
    pulse = int(MIN_PULSE + (angle / 180.0) * (MAX_PULSE - MIN_PULSE))
    write_pwm("duty_cycle", pulse)

def value_to_angle(value):
    # clamp input
    value = max(0.0, min(1.0, value))

    # linear map: 0→15, 0.5→97.5, 1→180
    return 15 + value * (180 - 15)

# --- MAIN ---

setup()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
sock.setblocking(False)

current_value = 0.5  # start centered

try:
    while True:
        # 🔹 flush all incoming packets (real-time)
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                current_value = float(data.decode())
            except BlockingIOError:
                break

        # 🔹 convert to angle and update servo
        angle = value_to_angle(current_value)
        set_angle(angle)

        # small delay to avoid hammering CPU
        time.sleep(0.02)

except KeyboardInterrupt:
    pass

finally:
    write_pwm("duty_cycle", "0")
    write_pwm("enable", "0")