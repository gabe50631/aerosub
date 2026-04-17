from periphery import GPIO
import time
import threading

# PIN CONFIGURATION - Easy to change
ENCODER_PIN_A   = 34    # Encoder channel A
ENCODER_PIN_B   = 48    # Encoder channel B
MOTOR_PIN_FWD   = 59    # Motor forward signal
MOTOR_PIN_REV   = 58    # Motor reverse signal
ZERO_BUTTON_PIN = 52    # Pushbutton for homing/zeroing

# MOTOR / ENCODER CONFIGURATION
MOTOR_INVERT        = False
ENCODER_INVERT      = False
ZERO_BUTTON_INVERT  = False
HOMING_DIRECTION    = "reverse"  # Direction to move during homing: "forward" or "reverse"
HOMING_TIMEOUT      = 30.0       # Seconds before homing gives up

# POSITION CONFIGURATION
POSITION_TOLERANCE  =    2   # +/- counts considered "at position"

# GLOBALS
encoder_position = 0
encoder_lock     = threading.Lock()
last_A = False
last_B = False

# GPIO SETUP
enc_A       = GPIO(ENCODER_PIN_A,   "in")
enc_B       = GPIO(ENCODER_PIN_B,   "in")
motor_fwd   = GPIO(MOTOR_PIN_FWD,   "out")
motor_rev   = GPIO(MOTOR_PIN_REV,   "out")
zero_button = GPIO(ZERO_BUTTON_PIN, "in")

# BUTTON READ
def button_pressed(): 
    """
    Returns True when the zero button is physically pressed.
    """
    state = zero_button.read()
    return (not state) if ZERO_BUTTON_INVERT else state


# MOTOR CONTROL
def motor_forward():
    if not MOTOR_INVERT:
        motor_rev.write(False)
        motor_fwd.write(True)
    else:
        motor_fwd.write(False)
        motor_rev.write(True)

def motor_reverse():
    if not MOTOR_INVERT:
        motor_fwd.write(False)
        motor_rev.write(True)
    else:
        motor_rev.write(False)
        motor_fwd.write(True)

def motor_stop():
    motor_fwd.write(False)
    motor_rev.write(False)

# X4 ENCODER DECODING
X4_TABLE = [
    0,  1, -1,  0,
   -1,  0,  0,  1,
    1,  0,  0, -1,
    0, -1,  1,  0,
]

def encoder_thread_func():
    """
    Continuously polls encoder pins and updates
    position using X4 decoding. Runs as daemon thread.
    """
    global encoder_position, last_A, last_B

    last_A = enc_A.read()
    last_B = enc_B.read()

    while True:
        curr_A = enc_A.read()
        curr_B = enc_B.read()

        if curr_A != last_A or curr_B != last_B:
            index = (int(last_A) << 3) | (int(last_B) << 2) | \
                    (int(curr_A) << 1) |  int(curr_B)
            delta = X4_TABLE[index]

            if ENCODER_INVERT:
                delta = -delta

            with encoder_lock:
                encoder_position += delta

            last_A = curr_A
            last_B = curr_B

def get_position():
    with encoder_lock:
        return encoder_position

def set_position(value):
    with encoder_lock:
        global encoder_position
        encoder_position = value


# HOMING
# Moves motor in HOMING_DIRECTION until the zero button is pressed, then zeros encoder position.
def home_motor():
    print("\n  === HOMING ===")
    print(f"  Moving {HOMING_DIRECTION} until button pressed...")
    print(f"  Timeout: {HOMING_TIMEOUT}s  |  Button pin: {ZERO_BUTTON_PIN}")

    start_time = time.time()

    try:
        # Drive in homing direction
        if HOMING_DIRECTION == "forward":
            motor_forward()
        else:
            motor_reverse()

        while not button_pressed():
            if time.time() - start_time > HOMING_TIMEOUT:
                motor_stop()
                print("  Homing FAILED: timeout reached.")
                return False
            time.sleep(0.001)

        motor_stop()
        set_position(0)
        print(f"  Homing SUCCESS. Encoder zeroed at button press.")
        print(f"  Position is now: {get_position()}")
        return True

    except KeyboardInterrupt:
        motor_stop()
        print("\n  Homing cancelled.")
        return False


# MOVE TO TARGET POSITION
def move_to_position(target, timeout=30.0):
    """
    Drive motor toward target encoder position.
    Returns True if reached, False if timed out.
    """
    start_time = time.time()
    print(f"  Moving to position: {target}")

    while True:
        pos   = get_position()
        error = target - pos

        if abs(error) <= POSITION_TOLERANCE:
            motor_stop()
            print(f"  Reached position: {pos}  (target={target})")
            return True

        if error > 0:
            motor_forward()
        else:
            motor_reverse()

        if time.time() - start_time > timeout:
            motor_stop()
            print(f"  Timeout! Current position: {pos}  (target={target})")
            return False

        time.sleep(0.001)

# MANUAL POSITION MODE
def manual_mode():
    print("\n=== MANUAL MODE ===")
    print("  Enter a target encoder position.")
    print(f"  Current position: {get_position()}")
    print("  Type 'q' to go back.\n")

    while True:
        try:
            user_input = input("  Target position: ").strip()
            if user_input.lower() == 'q':
                break

            target = int(user_input)
            move_to_position(target)

        except ValueError:
            print("  Invalid input. Enter an integer or 'q'.")
        except KeyboardInterrupt:
            motor_stop()
            print("\n  Manual mode stopped.")
            break

# MAIN MENU
def main():
    enc_thread = threading.Thread(target=encoder_thread_func, daemon=True)
    enc_thread.start()
    print("Encoder thread started.")

    try:
        while True:
            print("=============================")
            print(" [1] Manual mode      (enter position)")
            print(" [2] Home / Zero      (run to button)")
            print("=============================")

            choice = input(" Select: ").strip()

            if   choice == '1':
                manual_mode()
            elif choice == '2':
                home_motor()
                
    except KeyboardInterrupt:
        pass

    finally:
        motor_stop()
        enc_A.close()
        enc_B.close()
        motor_fwd.close()
        motor_rev.close()
        zero_button.close()
        print("\nGPIO closed. Goodbye.")

if __name__ == "__main__":
    main()