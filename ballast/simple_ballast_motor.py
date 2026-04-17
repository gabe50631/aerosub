from periphery import GPIO
import time
import threading

MOTOR_2_PIN_FWD = 51    # Motor 2 forward signal
MOTOR_2_PIN_REV = 4     # Motor 2 reverse signal

motor2_fwd   = GPIO(MOTOR_2_PIN_FWD,  "out")
motor2_rev   = GPIO(MOTOR_2_PIN_REV,  "out")


motor2_fwd.write(True)
motor2_rev.write(False)

time.sleep(1)

motor2_fwd.write(False)
motor2_rev.write(False)

time.sleep(1)

motor2_fwd.write(False)
motor2_rev.write(True)

time.sleep(1)