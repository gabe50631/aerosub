import time
import os

PWM_PATH = "/sys/class/pwm/pwmchip9/pwm0"

def write_val(file, value):
    with open(f"{PWM_PATH}/{file}", "w") as f:
        f.write(str(value))

def kickstart():
    # 1. Arm at Neutral
    write_val("enable", "0")
    write_val("period", "20000000")
    write_val("duty_cycle", "1500000")
    write_val("enable", "1")
    print(">>> Arming... wait for 5 beeps")
    time.sleep(6)

    # 2. The Kick (15% throttle for 0.2 seconds)
    print(">>> KICKSTARTING...")
    write_val("duty_cycle", "1575000") 
    time.sleep(0.2)
    
    # 3. Settle to 5%
    write_val("duty_cycle", "1525000")
    print(">>> Attempting steady rotation at 5%.")
    time.sleep(5)

try:
    if not os.path.exists(PWM_PATH):
        with open("/sys/class/pwm/pwmchip9/export", "w") as f: f.write("0")
    kickstart()
finally:
    write_val("duty_cycle", "1500000")
    write_val("enable", "0")
