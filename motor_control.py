import time
import os

# Using PWM9_M0 on pwmchip9 as specified
PWM_PATH = "/sys/class/pwm/pwmchip9/pwm0"
CHIP_PATH = "/sys/class/pwm/pwmchip9"

def write_val(file, value):
    with open(f"{PWM_PATH}/{file}", "w") as f:
        f.write(str(value))

def initialize_hardware():
    # 1. Export if needed
    if not os.path.exists(PWM_PATH):
        with open(f"{CHIP_PATH}/export", "w") as f:
            f.write("0")
        time.sleep(1)
    
    # 2. Set period to 50Hz (20,000,000ns)
    write_val("enable", "0")
    write_val("period", "20000000")
    write_val("polarity", "normal") # Ensure polarity is standard
    write_val("duty_cycle", "1500000")
    write_val("enable", "1")

def find_arm_point():
    print(">>> Searching for Arming Point. Listen for a change in beeping...")
    # Sweep slightly around 1500us in case of timing drift
    points = [1500000, 1480000, 1520000, 1450000, 1550000]
    
    for pt in points:
        print(f"Trying pulse: {pt}ns...")
        write_val("duty_cycle", str(pt))
        time.sleep(3)
        # If beeping stops or changes to a 'happy' long beep, we found it!

def run_test():
    initialize_hardware()
    find_arm_point()
    
    # If it armed, try a very slow crawl
    print("Testing slow forward...")
    write_val("duty_cycle", "1550000") # Tiny bit forward
    time.sleep(2)
    write_val("duty_cycle", "1500000") # Stop
    print("Test complete.")

try:
    run_test()
except KeyboardInterrupt:
    write_val("duty_cycle", "1500000")
    write_val("enable", "0")
