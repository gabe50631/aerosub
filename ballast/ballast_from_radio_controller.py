from periphery import GPIO
import time
import threading
import socket

command_queue = []
queue_lock = threading.Lock()

# ─────────────────────────────────────────
# PIN CONFIGURATION - Easy to change
# ─────────────────────────────────────────
ENCODER_PIN_A   = 34    # Encoder channel A
ENCODER_PIN_B   = 48    # Encoder channel B

MOTOR_PIN_FWD   = 59    # Motor forward signal
MOTOR_PIN_REV   = 58    # Motor reverse signal

ZERO_BUTTON_PIN = 52    # Pushbutton for homing/zeroing

# ─────────────────────────────────────────
# MOTOR / ENCODER CONFIGURATION
# ─────────────────────────────────────────
MOTOR_INVERT        = False   # Swap forward/reverse if motor runs backwards
ENCODER_INVERT      = False   # Swap encoder direction if counts go wrong way

ZERO_BUTTON_INVERT  = False   # True if button reads HIGH when not pressed
                               # (i.e. pull-up wired, active LOW)

HOMING_DIRECTION    = "reverse"  # Direction to move during homing: "forward" or "reverse"
HOMING_TIMEOUT      = 30.0       # Seconds before homing gives up

# ─────────────────────────────────────────
# POSITION CONFIGURATION
# ─────────────────────────────────────────
AUTO_FORWARD_TARGET = 1000   # Encoder counts forward limit
AUTO_REVERSE_TARGET =    0   # Encoder counts reverse limit
POSITION_TOLERANCE  =    2   # +/- counts considered "at position"

# ─────────────────────────────────────────
# GLOBALS
# ─────────────────────────────────────────
encoder_position = 0
encoder_lock     = threading.Lock()

last_A = False
last_B = False

# ─────────────────────────────────────────
# GPIO SETUP
# ─────────────────────────────────────────
enc_A       = GPIO(ENCODER_PIN_A,   "in")
enc_B       = GPIO(ENCODER_PIN_B,   "in")
motor_fwd   = GPIO(MOTOR_PIN_FWD,   "out")
motor_rev   = GPIO(MOTOR_PIN_REV,   "out")
zero_button = GPIO(ZERO_BUTTON_PIN, "in")

# ─────────────────────────────────────────
# LISTEN FOR CONTROLLER INPUTS
# ─────────────────────────────────────────
def network_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 5005))

    print("Network control listening on port 5005...")

    while True:
        data, _ = sock.recvfrom(1024)
        cmd = data.decode().strip()

        with queue_lock:
            command_queue.append(cmd)

            
# ─────────────────────────────────────────
# BUTTON READ
# ─────────────────────────────────────────
def button_pressed():
    """
    Returns True when the zero button is physically pressed.
    Handles active-low wiring via ZERO_BUTTON_INVERT.
    """
    state = zero_button.read()
    return (not state) if ZERO_BUTTON_INVERT else state


# ─────────────────────────────────────────
# MOTOR CONTROL
# Respects MOTOR_INVERT flag.
# ─────────────────────────────────────────
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


# ─────────────────────────────────────────
# HOMING / ZEROING ROUTINE
# Moves motor in HOMING_DIRECTION until
# the zero button is pressed, then zeros
# the encoder position.
# ─────────────────────────────────────────
def home_motor():
    print("\n  === HOMING ===")
    print(f"  Moving {HOMING_DIRECTION} until button pressed...")
    print(f"  Timeout: {HOMING_TIMEOUT}s  |  Button pin: {ZERO_BUTTON_PIN}")
    print("  Press Ctrl+C to cancel.\n")

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


# ─────────────────────────────────────────
# MOVE TO TARGET POSITION
# ─────────────────────────────────────────
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
            move_to_position(AUTO_FORWARD_TARGET)
            time.sleep(0.5)
            move_to_position(AUTO_REVERSE_TARGET)
            time.sleep(0.5)
    except KeyboardInterrupt:
        motor_stop()
        print("\n  Auto mode stopped.")


# ─────────────────────────────────────────
# MANUAL POSITION MODE
# ─────────────────────────────────────────
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


# ─────────────────────────────────────────
# CONFIGURATION MENU
# Change pin numbers and invert flags
# at runtime without restarting.
# ─────────────────────────────────────────
def config_menu():
    global ENCODER_PIN_A, ENCODER_PIN_B
    global MOTOR_PIN_FWD, MOTOR_PIN_REV
    global ZERO_BUTTON_PIN
    global MOTOR_INVERT, ENCODER_INVERT, ZERO_BUTTON_INVERT
    global HOMING_DIRECTION, HOMING_TIMEOUT
    global AUTO_FORWARD_TARGET, AUTO_REVERSE_TARGET, POSITION_TOLERANCE
    global enc_A, enc_B, motor_fwd, motor_rev, zero_button

    while True:
        print("\n=== CONFIGURATION ===")
        print(f"  [1] Encoder Pin A        : {ENCODER_PIN_A}")
        print(f"  [2] Encoder Pin B        : {ENCODER_PIN_B}")
        print(f"  [3] Motor Forward Pin    : {MOTOR_PIN_FWD}")
        print(f"  [4] Motor Reverse Pin    : {MOTOR_PIN_REV}")
        print(f"  [5] Zero Button Pin      : {ZERO_BUTTON_PIN}")
        print(f"  ─────────────────────────────")
        print(f"  [6] Invert Motor Dir     : {MOTOR_INVERT}")
        print(f"  [7] Invert Encoder Dir   : {ENCODER_INVERT}")
        print(f"  [8] Invert Button Logic  : {ZERO_BUTTON_INVERT}")
        print(f"  ─────────────────────────────")
        print(f"  [9] Homing Direction     : {HOMING_DIRECTION}")
        print(f" [10] Homing Timeout (s)   : {HOMING_TIMEOUT}")
        print(f"  ─────────────────────────────")
        print(f" [11] Auto Forward Target  : {AUTO_FORWARD_TARGET}")
        print(f" [12] Auto Reverse Target  : {AUTO_REVERSE_TARGET}")
        print(f" [13] Position Tolerance   : {POSITION_TOLERANCE}")
        print(f"  ─────────────────────────────")
        print(f"  [q] Back to main menu")
        print("======================")

        choice = input("  Select: ").strip().lower()

        # ── Pin reassignment helpers ──────────────────────────
        def reassign_pin(old_gpio, pin_name):
            """Close old GPIO, open new one, return new GPIO object."""
            try:
                new_pin = int(input(f"  New pin for {pin_name} (current={old_gpio.pin if hasattr(old_gpio, 'pin') else '?'}): "))
                old_gpio.close()
                return new_pin
            except ValueError:
                print("  Invalid pin number.")
                return None

        if choice == '1':
            enc_A.close()
            try:
                ENCODER_PIN_A = int(input(f"  New Encoder Pin A (current={ENCODER_PIN_A}): "))
                enc_A = GPIO(ENCODER_PIN_A, "in")
                print(f"  Encoder Pin A set to {ENCODER_PIN_A}")
            except ValueError:
                print("  Invalid. Keeping old pin.")
                enc_A = GPIO(ENCODER_PIN_A, "in")

        elif choice == '2':
            enc_B.close()
            try:
                ENCODER_PIN_B = int(input(f"  New Encoder Pin B (current={ENCODER_PIN_B}): "))
                enc_B = GPIO(ENCODER_PIN_B, "in")
                print(f"  Encoder Pin B set to {ENCODER_PIN_B}")
            except ValueError:
                print("  Invalid. Keeping old pin.")
                enc_B = GPIO(ENCODER_PIN_B, "in")

        elif choice == '3':
            motor_stop()
            motor_fwd.close()
            try:
                MOTOR_PIN_FWD = int(input(f"  New Motor Forward Pin (current={MOTOR_PIN_FWD}): "))
                motor_fwd = GPIO(MOTOR_PIN_FWD, "out")
                print(f"  Motor Forward Pin set to {MOTOR_PIN_FWD}")
            except ValueError:
                print("  Invalid. Keeping old pin.")
                motor_fwd = GPIO(MOTOR_PIN_FWD, "out")

        elif choice == '4':
            motor_stop()
            motor_rev.close()
            try:
                MOTOR_PIN_REV = int(input(f"  New Motor Reverse Pin (current={MOTOR_PIN_REV}): "))
                motor_rev = GPIO(MOTOR_PIN_REV, "out")
                print(f"  Motor Reverse Pin set to {MOTOR_PIN_REV}")
            except ValueError:
                print("  Invalid. Keeping old pin.")
                motor_rev = GPIO(MOTOR_PIN_REV, "out")

        elif choice == '5':
            zero_button.close()
            try:
                ZERO_BUTTON_PIN = int(input(f"  New Zero Button Pin (current={ZERO_BUTTON_PIN}): "))
                zero_button = GPIO(ZERO_BUTTON_PIN, "in")
                print(f"  Zero Button Pin set to {ZERO_BUTTON_PIN}")
            except ValueError:
                print("  Invalid. Keeping old pin.")
                zero_button = GPIO(ZERO_BUTTON_PIN, "in")

        elif choice == '6':
            MOTOR_INVERT = not MOTOR_INVERT
            print(f"  Motor Invert is now: {MOTOR_INVERT}")

        elif choice == '7':
            ENCODER_INVERT = not ENCODER_INVERT
            print(f"  Encoder Invert is now: {ENCODER_INVERT}")

        elif choice == '8':
            ZERO_BUTTON_INVERT = not ZERO_BUTTON_INVERT
            print(f"  Button Invert is now: {ZERO_BUTTON_INVERT}")

        elif choice == '9':
            d = input("  Homing direction ('forward' or 'reverse'): ").strip().lower()
            if d in ("forward", "reverse"):
                HOMING_DIRECTION = d
                print(f"  Homing direction set to: {HOMING_DIRECTION}")
            else:
                print("  Invalid. Must be 'forward' or 'reverse'.")

        elif choice == '10':
            try:
                HOMING_TIMEOUT = float(input(f"  New homing timeout in seconds (current={HOMING_TIMEOUT}): "))
                print(f"  Homing timeout set to: {HOMING_TIMEOUT}s")
            except ValueError:
                print("  Invalid number.")

        elif choice == '11':
            try:
                AUTO_FORWARD_TARGET = int(input(f"  New auto forward target (current={AUTO_FORWARD_TARGET}): "))
                print(f"  Auto forward target set to: {AUTO_FORWARD_TARGET}")
            except ValueError:
                print("  Invalid number.")

        elif choice == '12':
            try:
                AUTO_REVERSE_TARGET = int(input(f"  New auto reverse target (current={AUTO_REVERSE_TARGET}): "))
                print(f"  Auto reverse target set to: {AUTO_REVERSE_TARGET}")
            except ValueError:
                print("  Invalid number.")

        elif choice == '13':
            try:
                POSITION_TOLERANCE = int(input(f"  New position tolerance (current={POSITION_TOLERANCE}): "))
                print(f"  Position tolerance set to: {POSITION_TOLERANCE}")
            except ValueError:
                print("  Invalid number.")

        elif choice == 'q':
            break
        else:
            print("  Invalid choice.")


# ─────────────────────────────────────────
# MAIN MENU
# ─────────────────────────────────────────
def main():
    net_thread = threading.Thread(target=network_listener, daemon=True)
    net_thread.start()

    def get_next_command():
        with queue_lock:
            if command_queue:
                return command_queue.pop(0)
        return None
    


    enc_thread = threading.Thread(target=encoder_thread_func, daemon=True)
    enc_thread.start()
    print("Encoder thread started.")

    try:
        while True:
            print("\n=============================")
            print(f" Current position : {get_position()}")
            print(f" Button pressed   : {button_pressed()}")
            print("=============================")
            print(" [1] Auto mode        (back-and-forth)")
            print(" [2] Manual mode      (enter position)")
            print(" [3] Home / Zero      (run to button)")
            print(" [4] Reset position   (zero without moving)")
            print(" [5] Configuration    (pins, invert, limits)")
            print(" [6] Exit")
            print("=============================")

            # get input from controller
            cmd = get_next_command()
            if cmd:
                choice = cmd
            else:
                choice = input(" Select: ").strip()



            if   choice == '1':
                auto_mode()
            elif choice == '2':
                manual_mode()
            elif choice == '3':
                home_motor()
            elif choice == '4':
                set_position(0)
                print(f" Position reset to 0 (motor did not move).")
            elif choice == '5':
                config_menu()
            elif choice == '6':
                break
            else:
                print(" Invalid choice.")

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
