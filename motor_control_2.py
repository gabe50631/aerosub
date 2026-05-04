import time
import os

# Configuration
PWM_PATH = "/sys/class/pwm/pwmchip9/pwm0"
PERIOD = 20000000  # 50Hz (20ms)
NEUTRAL = 1500000  # 1.5ms - The Stop signal

def write_pwm(file, value):
    with open(f"{PWM_PATH}/{file}", "w") as f:
        f.write(str(value))

def setup():
    if not os.path.exists(PWM_PATH):
        with open("/sys/class/pwm/pwmchip9/export", "w") as f:
            f.write("0")
    time.sleep(2)
    write_pwm("period", PERIOD)
    write_pwm("duty_cycle", NEUTRAL)
    write_pwm("enable", "1")
    print(">>> ESC Initialized at Neutral (1500000ns).")
    print(">>> Wait 5 seconds for arming beeps...")
    time.sleep(5)

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

try:
    setup()
    print("\n--- ApisQueen U2 Mini Control ---")
    print("Enter speed from -100 to 100 (0 to stop). Type 'exit' to quit.")
    
    while True:
        user_input = input("Target Speed %: ").strip().lower()
        
        if user_input == 'exit':
            break
            
        try:
            val = int(user_input)
            actual_pulse = set_speed(val)
            print(f"Set to {val}% (Pulse: {actual_pulse}ns)")
        except ValueError:
            print("Invalid input. Please enter a number.")

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    set_speed(0)
    # Keeping enable=1 is often better for ESCs to stay armed, 
    # but we'll disable it for safety on exit.
    write_pwm("enable", "0")