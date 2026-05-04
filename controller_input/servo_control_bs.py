import time
import os
import socket
import struct


# pwm configuration
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
    PWM_CHIP = "/sys/class/pwm/pwmchip9"
    PWM_PATH = PWM_CHIP + "/pwm0"

    # ensure pwmchip exists
    if not os.path.exists(PWM_CHIP):
        raise RuntimeError("pwmchip9 does not exist")

    # export if needed
    if not os.path.exists(PWM_PATH):
        try:
            with open(PWM_CHIP + "/export", "w") as f:
                f.write("0")
        except OSError:
            pass  # already exported or busy

        # wait until pwm0 appears
        timeout = time.time() + 1.0
        while not os.path.exists(PWM_PATH):
            if time.time() > timeout:
                raise RuntimeError("PWM export failed")
            time.sleep(0.01)

    # now safe to configure
    write_pwm("enable", "0")
    write_pwm("period", PERIOD)
    write_pwm("duty_cycle", 1500000)
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
sock.bind(("0.0.0.0", 5005))
sock.setblocking(False)
rjx = rjy = ljy = ljx = rt = 0.0 # axes variables

current_value = 0.5  # start centered

try:
    while True:
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                rjx, rjy, ljy, ljx, rt = struct.unpack("5f", data)
                current_value = rjx
                current_value = (current_value + 1) / 2 # range -> [0, 1]
            except BlockingIOError:
                break

        # convert to angle and update servo
        angle = value_to_angle(current_value)
        set_angle(angle)

        # small delay to avoid hammering CPU
        time.sleep(0.02)

except KeyboardInterrupt:
    pass

finally:
    write_pwm("duty_cycle", "0")
    write_pwm("enable", "0")