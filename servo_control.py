import time
import os

# Configuration
PWM_PATH = "/sys/class/pwm/pwmchip9/pwm0"
PERIOD = 20000000  # 20ms (50Hz)
MIN_PULSE = 1000000  # 1.0ms (Standard 0°)
MAX_PULSE = 2000000  # 2.0ms (Standard 180°)
CENTER    = 1500000  # 1.5ms (90°)

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
    
    # 1. Disable first to allow parameter changes
    write_pwm("enable", "0")
    # 2. Set duty to 0 to prevent "duty > period" errors
    write_pwm("duty_cycle", "0")
    # 3. Set the 50Hz period
    write_pwm("period", PERIOD)
    # 4. Set starting position
    write_pwm("duty_cycle", CENTER)
    # 5. Finally enable
    write_pwm("enable", "1")
    print(">>> MG90S Initialized at Center.")

def set_angle(angle):
    # Change the lower limit from 0 to 15
    # This prevents the pulse from dropping below the "failure" threshold
    angle = max(15, min(180, angle))
    
    pulse = int(MIN_PULSE + (angle / 180.0) * (MAX_PULSE - MIN_PULSE))
    write_pwm("duty_cycle", pulse)
    return pulse

try:
    setup()
    while True:
        user_input = input("Target Angle (0-180): ").strip().lower()
        if user_input == 'exit': break
        try:
            val = int(user_input)
            set_angle(val)
        except ValueError:
            print("Enter a number.")
except KeyboardInterrupt:
    pass
finally:
    # Clean exit: zero out duty before disabling
    write_pwm("duty_cycle", "0")
    write_pwm("enable", "0")
