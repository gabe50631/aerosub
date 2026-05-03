import time
import os
import socket
import struct

# Configuration
PWM_PATH_1 = "/sys/class/pwm/pwmchip9/pwm0" # Servo
PWM_PATH_2 = "/sys/class/pwm/pwmchip8/pwm0" # Thruster
PERIOD = 20000000  # 20ms (50Hz)
NEUTRAL = 1500000  # 1.5ms - stop
MIN_PULSE = 1000000
MAX_PULSE = 2000000

# UDP setup
PORT = 5005

def write_pwm(path, file, value):
    """Writes a value to a specific PWM path (3 arguments required)."""
    try:
        with open(f"{path}/{file}", "w") as f:
            f.write(str(value))
    except OSError as e:
        print(f"Error writing {value} to {path}/{file}: {e}")

def setup():
    PWM_CHIP_1 = "/sys/class/pwm/pwmchip9"
    PWM_CHIP_2 = "/sys/class/pwm/pwmchip8"

    # Ensure pwmchip directories exist
    if not (os.path.exists(PWM_CHIP_1) and os.path.exists(PWM_CHIP_2)):
        raise RuntimeError("A pwmchip does not exist. Check your hardware overlay/Luckfox config.")

    # Export PWM channels if they aren't visible
    for chip, path in [(PWM_CHIP_1, PWM_PATH_1), (PWM_CHIP_2, PWM_PATH_2)]:
        if not os.path.exists(path):
            try:
                with open(chip + "/export", "w") as f:
                    f.write("0")
            except OSError:
                pass
            timeout = time.time() + 2.0
            while not os.path.exists(path):
                if time.time() > timeout:
                    raise RuntimeError(f"PWM export failed for {path}")
                time.sleep(0.1)

    # INITIALIZE BOTH CHIPS (Fixes the TypeError)
    for path in [PWM_PATH_1, PWM_PATH_2]:
        write_pwm(path, "enable", "0")       # 1. Disable first
        write_pwm(path, "period", PERIOD)    # 2. Set period (20ms)
        write_pwm(path, "duty_cycle", NEUTRAL) # 3. Set to stop/neutral
        write_pwm(path, "enable", "1")       # 4. Enable output

    print(">>> ESC & Servo Initialized at Neutral.")
    print(">>> Wait 5 seconds for arming beeps...")
    time.sleep(5)
    print(">>> Motors Ready")

def set_angle(angle):
    """Servo control (15-180 degrees)."""
    angle = max(15, min(180, angle))
    pulse = int(MIN_PULSE + (angle / 180.0) * (MAX_PULSE - MIN_PULSE))
    write_pwm(PWM_PATH_1, "duty_cycle", pulse)

def value_to_angle(value):
    """Maps 0.0-1.0 to 15-180 degrees."""
    value = max(0.0, min(1.0, value))
    return 15 + value * (180 - 15)

def set_speed(percent):
    """Bi-directional ESC control (-100 to 100 percent)."""
    percent = max(-100, min(100, percent))
    pulse = NEUTRAL + (percent * 5000)
    write_pwm(PWM_PATH_2, "duty_cycle", int(pulse))
    return int(pulse)

# --- MAIN ---

setup()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
sock.setblocking(False)

servo_val = 0.5
thruster_percent = 0

try:
    while True:
        # Get latest packet from buffer
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                rjx, rjy, ljy, ljx, rt = struct.unpack("5f", data)
                
                # Servo: rjx is -1 to 1, map to 0 to 1
                servo_val = (rjx + 1) / 2
                
                # Thruster: rjy is -1 to 1, map to -100 to 100
                thruster_percent = rjy * 100
            except BlockingIOError:
                break

        # Update hardware
        set_angle(value_to_angle(servo_val))
        set_speed(thruster_percent)
        
        # print(f"Thruster: {thruster_percent}%") # Debug toggle

        time.sleep(0.02)

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    # Set to neutral and stop for safety
    for path in [PWM_PATH_1, PWM_PATH_2]:
        write_pwm(path, "duty_cycle", NEUTRAL)
        write_pwm(path, "enable", "0")
