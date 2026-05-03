import time
import os
import socket
import struct


# Configuration
PWM_PATH_1 = "/sys/class/pwm/pwmchip9/pwm0"
PWM_PATH_2 = "/sys/class/pwm/pwmchip8/pwm0"
PERIOD = 20000000  # 20ms (50Hz)
NEUTRAL = 1500000  # 1.5ms - stop
MIN_PULSE = 1000000
MAX_PULSE = 2000000

# UDP setup
PORT = 5005

def write_pwm(file, value_1, value_2):
    try:
        with open(f"{PWM_PATH_1}/{file}", "w") as f:
            f.write(str(value_1))
        with open(f"{PWM_PATH_2}/{file}", "w") as f:
            f.write(str(value_2))
    except OSError as e:
        print(f"Error writing to {file}: {e}")

def setup():
    PWM_CHIP_1 = "/sys/class/pwm/pwmchip9"
    PWM_CHIP_2 = "/sys/class/pwm/pwmchip8"
    PWM_PATH_1 = PWM_CHIP_1 + "/pwm0"    
    PWM_PATH_2 = PWM_CHIP_2 + "/pwm0"

    # ensure pwmchip exists
    if not (os.path.exists(PWM_CHIP_1) and os.path.exists(PWM_CHIP_2)):
        raise RuntimeError("a pwmchip does not exist")

    # export if needed
    if not os.path.exists(PWM_PATH_1):
        try:
            with open(PWM_CHIP_1 + "/export", "w") as f:
                f.write("0")
        except OSError:
            pass  # already exported or busy
        # wait until pwm0 appears
        timeout = time.time() + 1.0
        while not os.path.exists(PWM_PATH_1):
            if time.time() > timeout:
                raise RuntimeError("PWM export failed")
            time.sleep(0.01)

    if not os.path.exists(PWM_PATH_2):
        try:
            with open(PWM_CHIP_2 + "/export", "w") as f:
                f.write("0")
        except OSError:
            pass  # already exported or busy

        # wait until pwm0 appears
        timeout = time.time() + 1.0
        while not os.path.exists(PWM_PATH_2):
            if time.time() > timeout:
                raise RuntimeError("PWM export failed")
            time.sleep(0.01)

    # now safe to configure
    write_pwm("enable", "0")
    write_pwm("period", PERIOD)
    write_pwm("duty_cycle", NEUTRAL)
    write_pwm("enable", "1")
    print(">>> ESC Initialized at Neutral (1500000ns).")
    print(">>> Wait 5 seconds for arming beeps...")
    time.sleep(5)

    print(">>> Motors Ready")

def set_angle(angle):
    angle = max(15, min(180, angle))
    pulse = int(MIN_PULSE + (angle / 180.0) * (MAX_PULSE - MIN_PULSE))
    write_pwm("duty_cycle", pulse)

def value_to_angle(value):
    # clamp input
    value = max(0.0, min(1.0, value))

    # linear map: 0→15, 0.5→97.5, 1→180
    return 15 + value * (180 - 15)

def set_speed(percent):
    """
    percent: -100 to 100
    Reverse: 1000000ns to 1500000ns
    Forward: 1500000ns to 2000000ns
    """
    # Safety clamp
    percent = max(-100, min(100, percent))
    
    # Calculate pulse width in nanoseconds
    pulse = NEUTRAL + (percent * 5000)
    write_pwm("duty_cycle", int(pulse))
    return int(pulse)


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