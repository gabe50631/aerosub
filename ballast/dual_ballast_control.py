from periphery import GPIO
import time
import threading

# ─────────────────────────────────────────
# PIN CONFIGURATION
# ─────────────────────────────────────────
ENCODER_PIN_A   = 34    # Motor 1 encoder channel A
ENCODER_PIN_B   = 48    # Motor 1 encoder channel B
ENCODER_PIN_C   = 49    # Motor 2 encoder channel A
ENCODER_PIN_D   = 50    # Motor 2 encoder channel B

MOTOR_1_PIN_FWD = 59    # Motor 1 forward signal
MOTOR_1_PIN_REV = 58    # Motor 1 reverse signal
MOTOR_2_PIN_FWD = 51    # Motor 2 forward signal
MOTOR_2_PIN_REV = 4     # Motor 2 reverse signal

ZERO_BUTTON_1_PIN = 52  # Motor 1 home/zero button
ZERO_BUTTON_2_PIN = 56  # Motor 2 home/zero button

# ─────────────────────────────────────────
# MOTOR / ENCODER CONFIGURATION
# ─────────────────────────────────────────
MOTOR_1_INVERT   = False
MOTOR_2_INVERT   = False
ENCODER_1_INVERT = False
ENCODER_2_INVERT = False

ZERO_BUTTON_INVERT = False   # Applies to both buttons

HOMING_DIRECTION = "reverse" # "forward" or "reverse"
HOMING_TIMEOUT   = 30.0

# ─────────────────────────────────────────
# POSITION CONFIGURATION
# ─────────────────────────────────────────
AUTO_FORWARD_TARGET = 1000
AUTO_REVERSE_TARGET = 0
POSITION_TOLERANCE  = 2

# ─────────────────────────────────────────
# ENCODER STATE (two independent encoders)
# ─────────────────────────────────────────
encoder_positions = [0, 0]
encoder_lock      = threading.Lock()

last_A = [False, False]
last_B = [False, False]

# ─────────────────────────────────────────
# GPIO SETUP
# ─────────────────────────────────────────
enc_A        = GPIO(ENCODER_PIN_A,    "in")
enc_B        = GPIO(ENCODER_PIN_B,    "in")
enc_C        = GPIO(ENCODER_PIN_C,    "in")
enc_D        = GPIO(ENCODER_PIN_D,    "in")

motor1_fwd   = GPIO(MOTOR_1_PIN_FWD,  "out")
motor1_rev   = GPIO(MOTOR_1_PIN_REV,  "out")
motor2_fwd   = GPIO(MOTOR_2_PIN_FWD,  "out")
motor2_rev   = GPIO(MOTOR_2_PIN_REV,  "out")

zero_button1 = GPIO(ZERO_BUTTON_1_PIN, "in")
zero_button2 = GPIO(ZERO_BUTTON_2_PIN, "in")

# Group into lists for indexed access
enc_pins  = [(enc_A, enc_B), (enc_C, enc_D)]
mot_pins  = [(motor1_fwd, motor1_rev), (motor2_fwd, motor2_rev)]
mot_invert = [MOTOR_1_INVERT, MOTOR_2_INVERT]
enc_invert = [ENCODER_1_INVERT, ENCODER_2_INVERT]
buttons    = [zero_button1, zero_button2]

# ─────────────────────────────────────────
# BUTTON READ
# ─────────────────────────────────────────
def button_pressed(motor_idx):
    state = buttons[motor_idx].read()
    return (not state) if ZERO_BUTTON_INVERT else state

# ─────────────────────────────────────────
# MOTOR CONTROL
# ─────────────────────────────────────────
def motor_forward(motor_idx):
    fwd, rev = mot_pins[motor_idx]
    if not mot_invert[motor_idx]:
        rev.write(False)
        fwd.write(True)
    else:
        fwd.write(False)
        rev.write(True)

def motor_reverse(motor_idx):
    fwd, rev = mot_pins[motor_idx]
    if not mot_invert[motor_idx]:
        fwd.write(False)
        rev.write(True)
    else:
        rev.write(False)
        fwd.write(True)

def motor_stop(motor_idx):
    fwd, rev = mot_pins[motor_idx]
    fwd.write(False)
    rev.write(False)

def all_motors_stop():
    for i in range(2):
        motor_stop(i)

# ─────────────────────────────────────────
# X4 ENCODER DECODING
# ─────────────────────────────────────────
X4_TABLE = [
    0,  1, -1,  0,
   -1,  0,  0,  1,
    1,  0,  0, -1,
    0, -1,  1,  0,
]

def encoder_thread_func():
    global encoder_positions

    for i in range(2):
        last_A[i] = enc_pins[i][0].read()
        last_B[i] = enc_pins[i][1].read()

    while True:
        for i in range(2):
            pin_a, pin_b = enc_pins[i]
            curr_A = pin_a.read()
            curr_B = pin_b.read()

            if curr_A != last_A[i] or curr_B != last_B[i]:
                index = (int(last_A[i]) << 3) | (int(last_B[i]) << 2) | \
                        (int(curr_A)   << 1) |  int(curr_B)
                delta = X4_TABLE[index]

                if enc_invert[i]:
                    delta = -delta

                with encoder_lock:
                    encoder_positions[i] += delta

                last_A[i] = curr_A
                last_B[i] = curr_B

def get_position(motor_idx):
    with encoder_lock:
        return encoder_positions[motor_idx]

def set_position(motor_idx, value):
    with encoder_lock:
        encoder_positions[motor_idx] = value

# ─────────────────────────────────────────
# HOMING ROUTINE (independent per motor)
# Runs both motors simultaneously in
# HOMING_DIRECTION; each stops individually
# when its button is triggered.
# ─────────────────────────────────────────
def home_motor():
    print("\n=== HOMING ===")
    print(f"  Moving both motors {HOMING_DIRECTION} until buttons pressed...")
    print(f"  Timeout: {HOMING_TIMEOUT}s  |  Press Ctrl+C to cancel.\n")

    homed   = [False, False]
    start   = time.time()

    try:
        # Start both motors in homing direction
        for i in range(2):
            if HOMING_DIRECTION == "forward":
                motor_forward(i)
            else:
                motor_reverse(i)

        while not all(homed):
            if time.time() - start > HOMING_TIMEOUT:
                all_motors_stop()
                print("  Homing FAILED: timeout reached.")
                return False

            for i in range(2):
                if not homed[i] and button_pressed(i):
                    motor_stop(i)
                    set_position(i, 0)
                    homed[i] = True
                    print(f"  Motor {i+1} homed. Encoder {i+1} zeroed.")

            time.sleep(0.001)

        print("  Both motors homed successfully.")
        return True

    except KeyboardInterrupt:
        all_motors_stop()
        print("\n  Homing cancelled.")
        return False

# ─────────────────────────────────────────
# MOVE TO TARGET POSITION (single motor)
# ─────────────────────────────────────────
def move_to_position(motor_idx, target, timeout=30.0):
    start = time.time()

    while True:
        pos   = get_position(motor_idx)
        error = target - pos

        if abs(error) <= POSITION_TOLERANCE:
            motor_stop(motor_idx)
            return True

        motor_forward(motor_idx) if error > 0 else motor_reverse(motor_idx)

        if time.time() - start > timeout:
            motor_stop(motor_idx)
            print(f"  Motor {motor_idx+1} timeout at pos={pos}, target={target}")
            return False

        time.sleep(0.001)

# ─────────────────────────────────────────
# MOVE BOTH MOTORS TO SAME TARGET
# Uses two threads so they run in parallel.
# ─────────────────────────────────────────
def move_both_to_position(target, timeout=30.0):
    results = [False, False]

    def worker(i):
        results[i] = move_to_position(i, target, timeout)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return all(results)

# ─────────────────────────────────────────
# AUTO BACK-AND-FORTH MODE
# ─────────────────────────────────────────
def auto_mode():
    print("\n=== AUTO MODE ===")
    print(f"  Forward target : {AUTO_FORWARD_TARGET}")
    print(f"  Reverse target : {AUTO_REVERSE_TARGET}")
    print("  Press Ctrl+C to stop.\n")

    try:
        while True:
            print(f"  → Moving to {AUTO_FORWARD_TARGET}")
            move_both_to_position(AUTO_FORWARD_TARGET)
            time.sleep(0.5)
            print(f"  ← Moving to {AUTO_REVERSE_TARGET}")
            move_both_to_position(AUTO_REVERSE_TARGET)
            time.sleep(0.5)
    except KeyboardInterrupt:
        all_motors_stop()
        print("\n  Auto mode stopped.")

# ─────────────────────────────────────────
# MANUAL POSITION MODE
# ─────────────────────────────────────────
def manual_mode():
    print("\n=== MANUAL MODE ===")
    print("  Enter a target encoder position (both motors move together).")
    print(f"  Motor 1: {get_position(0)}  |  Motor 2: {get_position(1)}")
    print("  Type 'q' to go back.\n")

    while True:
        try:
            user_input = input("  Target position: ").strip()
            if user_input.lower() == 'q':
                break

            target = int(user_input)
            print(f"  Moving both motors to {target}...")
            move_both_to_position(target)
            print(f"  Done. Motor 1: {get_position(0)}  Motor 2: {get_position(1)}")

        except ValueError:
            print("  Invalid input. Enter an integer or 'q'.")
        except KeyboardInterrupt:
            all_motors_stop()
            print("\n  Manual mode stopped.")
            break

# ─────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────
def main():
    enc_thread = threading.Thread(target=encoder_thread_func, daemon=True)
    enc_thread.start()
    print("Encoder thread started.")

    try:
        while True:
            print("\n=============================")
            print(f" Motor 1 position : {get_position(0)}  |  Button: {button_pressed(0)}")
            print(f" Motor 2 position : {get_position(1)}  |  Button: {button_pressed(1)}")
            print("=============================")
            print(" [1] Auto mode    (back-and-forth, both motors)")
            print(" [2] Manual mode  (enter position, both motors)")
            print(" [3] Home / Zero  (run each to its button)")
            print(" [4] Exit")
            print("=============================")

            choice = input(" Select: ").strip()

            if   choice == '1':
                auto_mode()
            elif choice == '2':
                manual_mode()
            elif choice == '3':
                home_motor()
            elif choice == '4':
                break
            else:
                print(" Invalid choice.")

    except KeyboardInterrupt:
        pass

    finally:
        all_motors_stop()
        for pin in [enc_A, enc_B, enc_C, enc_D,
                    motor1_fwd, motor1_rev,
                    motor2_fwd, motor2_rev,
                    zero_button1, zero_button2]:
            pin.close()
        print("\nGPIO closed. Goodbye.")

if __name__ == "__main__":
    main()