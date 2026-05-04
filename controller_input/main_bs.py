import socket
import struct
import time
import threading
from periphery import GPIO
import serial

# PIN CONFIGURATION
ENCODER_PIN_A   = 34    # Motor 1 A
ENCODER_PIN_B   = 48    # Motor 1 B
ENCODER_PIN_C   = 49    # Motor 2 A
ENCODER_PIN_D   = 50    # Motor 2 B
MOTOR_1_PIN_FWD = 59    # Motor 1 fwd
MOTOR_1_PIN_REV = 58    # Motor 1 rev
MOTOR_2_PIN_FWD = 51    # Motor 2 fwd
MOTOR_2_PIN_REV = 4     # Motor 2 rev
ZERO_BUTTON_1_PIN = 52  # Zero button 1
ZERO_BUTTON_2_PIN = 56  # Zero button 2

HOMING_TIMEOUT      = 30.0   # Seconds before homing gives up
POSITION_TOLERANCE  = 2      # +/- counts considered "at position"

# GLOBALS
encoder_1_pos = [0]
encoder_2_pos = [0]
lock1     = threading.Lock()
lock2     = threading.Lock()
neutral_pos = 7500
ser = serial.Serial('/dev/ttyS5', baudrate=9600, timeout=1) # establish serial data out to arduino

# GPIO SETUP
enc_A       = GPIO(ENCODER_PIN_A,   "in")
enc_B       = GPIO(ENCODER_PIN_B,   "in")
enc_C       = GPIO(ENCODER_PIN_C,   "in")
enc_D       = GPIO(ENCODER_PIN_D,   "in")
m1_fwd      = GPIO(MOTOR_1_PIN_FWD,   "out")
m1_rev      = GPIO(MOTOR_1_PIN_REV,   "out")
m2_fwd      = GPIO(MOTOR_2_PIN_FWD,   "out")
m2_rev      = GPIO(MOTOR_2_PIN_REV,   "out")
zero_button_1 = GPIO(ZERO_BUTTON_1_PIN, "in")
zero_button_2 = GPIO(ZERO_BUTTON_2_PIN, "in")

# BUTTON READ - return true when button pressed
def button_1_pressed():
    state = zero_button_1.read()
    return (state)
def button_2_pressed():
    state = zero_button_2.read()
    return (state)

# MOTOR CONTROL
def motor_1_forward():
    m1_rev.write(False)
    m1_fwd.write(True)
def motor_2_forward():
    m2_rev.write(False)
    m2_fwd.write(True)

def motor_1_reverse():
    m1_fwd.write(False)
    m1_rev.write(True)
def motor_2_reverse():
    m2_fwd.write(False)
    m2_rev.write(True)

def motor_1_stop():
    m1_fwd.write(False)
    m1_rev.write(False)
def motor_2_stop():
    m2_fwd.write(False)
    m2_rev.write(False)

# X4 ENCODER DECODING
X4_TABLE = [
    0,  1, -1,  0,
   -1,  0,  0,  1,
    1,  0,  0, -1,
    0, -1,  1,  0,
]

# Polls encoder pins and updates position using X4 decoding. Runs as daemon thread
def encoder_thread_func(enc_A, enc_B, position, lock):
    last_A = enc_A.read()
    last_B = enc_B.read()

    while True:
        curr_A = enc_A.read()
        curr_B = enc_B.read()

        if curr_A != last_A or curr_B != last_B:
            index = (int(last_A) << 3) | (int(last_B) << 2) | \
                    (int(curr_A) << 1) |  int(curr_B)
            delta = X4_TABLE[index]

            with lock:
                position[0] += delta

            last_A = curr_A
            last_B = curr_B

def get_pos_1():
    with lock1:
        return encoder_1_pos[0]
def get_pos_2():
    with lock2:
        return encoder_2_pos[0]
def set_pos_1(value):
    with lock1:
        encoder_1_pos[0] = value
def set_pos_2(value):
    with lock2:
        encoder_2_pos[0] = value

# HOMING - Moves motor reverse until the zero button is pressed, then zeros encoder position
def home_motors():
    print("\n  === HOMING ===")
    start_time = time.time()
    btn_1_pressed = False
    btn_2_pressed = False

    try:
        # edge case if button 1 is pressed
        if button_1_pressed() and not(button_2_pressed()):
            motor_2_reverse()
            print("Reversing only motor 2")
        elif not(button_1_pressed()) and button_2_pressed():
            motor_1_reverse()
            print("Reversing only motor 1")
        # elif button_1_pressed() and button_2_pressed():
        #     # do nothing
        elif not(button_1_pressed()) and not(button_2_pressed()):
            motor_1_reverse()
            motor_2_reverse()
            print("Reversing both motors")

        print("Waiting for motors to reach home")
        while not (button_1_pressed() and button_2_pressed()):
            if time.time() - start_time > HOMING_TIMEOUT:
                motor_1_stop()
                motor_2_stop()
                print("  Homing FAILED: timeout reached.")
                return False
            if button_1_pressed():
                motor_1_stop()
                btn_1_pressed = True
            if button_2_pressed():
                motor_2_stop()
                btn_2_pressed = True
            if btn_1_pressed and btn_2_pressed:
                break
            time.sleep(0.001)

        motor_1_stop()
        motor_2_stop()
        set_pos_1(0)
        set_pos_2(0)
        print(f"  Homing SUCCESS. Encoder zeroed at button press.")
        print(f"  Position 1: {get_pos_1()}")
        print(f"  Position 2: {get_pos_2()}")
        return True

    except KeyboardInterrupt:
        motor_1_stop()
        motor_2_stop()
        print("\n  Homing cancelled.")
        return False


# Move to target position. Return true when reached or time out after 30 s
def move_to_position(target, timeout=30.0):
    start_time = time.time()

    m1_done = False
    m2_done = False

    # check if close enough already
    if (abs(get_pos_1() - target) < 200) and (abs(get_pos_2() - target) < 200):
        return True
    
    while True:
        pos_1 = get_pos_1()
        pos_2 = get_pos_2()
        print(f"pos1: {pos_1} pos2: {pos_2}") #removing this breaks encoding somehow

        error_1 = target - pos_1
        error_2 = target - pos_2

        # --- Motor 1 ---
        if not m1_done:
            if abs(error_1) <= POSITION_TOLERANCE:
                motor_1_stop()
                m1_done = True
                print(f"  Motor 1 reached: {pos_1}")
            elif error_1 > 0:
                motor_1_forward()
            else:
                motor_1_reverse()

        # --- Motor 2 ---
        if not m2_done:
            if abs(error_2) <= POSITION_TOLERANCE:
                motor_2_stop()
                m2_done = True
                print(f"  Motor 2 reached: {pos_2}")
            elif error_2 > 0:
                motor_2_forward()
            else:
                motor_2_reverse()

        # Exit only when BOTH are done
        if m1_done and m2_done:
            print(f"  Both motors reached target: {target}")
            return True

        # Timeout
        if time.time() - start_time > timeout:
            motor_1_stop()
            motor_2_stop()
            print(f"  Timeout. Positions: {pos_1}, {pos_2}")
            return False

        time.sleep(0.001)

# startup procedure
def ballast_startup():
    try:
        print("Homing motors")
        home_motors()
        print("Homing finished, moving to neutral position")
        move_to_position(neutral_pos)
                
    except KeyboardInterrupt:
        pass



def main():
    t1 = threading.Thread(target=encoder_thread_func, args=(enc_A, enc_B, encoder_1_pos, lock1), daemon=True)
    t2 = threading.Thread(target=encoder_thread_func, args=(enc_C, enc_D, encoder_2_pos, lock2), daemon=True)
    t1.start()
    t2.start()
    print("Encoder thread started.")
    #ballast_startup()
    print("Ballasts are ready for input")

    # receive data
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 5005))
    sock.setblocking(False)  # non-blocking
    rjx = rjy = ljy = ljx = rt = 0.0 # axes variables

    # front_right, front_left, back, horizontal
    arduino_data = [0, 0, 0, 0]

    last_print = time.time()

    try:
        while True:
            try:
                data, _ = sock.recvfrom(1024)
                rjx, rjy, ljy, ljx, rt = struct.unpack("5f", data)
            except BlockingIOError:
                pass  # no more packets

            # --- UPDATE BALLAST ---
            # ballast_pos = rt
            # if ballast_pos < -0.5:
            #     home_motors()
            # elif (ballast_pos < 0.5) and (ballast_pos > -0.5):
            #     move_to_position(neutral_pos)
            # elif ballast_pos > 0.5:
            #     move_to_position(neutral_pos*2)

            # --- UPDATE SERVO ---

            # --- UPDATE THRUSTERS ---
            # joystick value -> thruster throttle value
            # if ljy > 0, increse back, decrease front_right, front_left
            # if ljy < 0, decrease back, increase front_right, front_left
            # if ljx > 0, increase front_left, decrease front_right
            # if ljx < 0, decrease front_left, increase front_right
            arduino_data = [
                ((-1 * ljy) + (-1 * ljx)) / 2,      # front right
                ((-1 * ljy) + (ljx)) / 2,           # front left
                ljy,                                # back
                rjy                                 # horizontal
            ]
            
            formatted = [format(x, ".3f") for x in arduino_data]

            arduino_message = ",".join(formatted) + "\n"

            ser.write(arduino_message.encode('utf-8'))
            print("Sent:", arduino_message)

            

            now = time.time()
            if now - last_print >= 0.2:
                print(f"rjx: {rjx:.3f}, rjy: {rjy:.3f}, ljy: {ljy:.3f}, ljx: {ljx:.3f}, rt: {rt:.3f}")
                last_print = now
            
    except KeyboardInterrupt:
        pass

    finally:
            motor_1_stop()
            motor_2_stop()
            enc_A.close()
            enc_B.close()
            enc_C.close()
            enc_D.close()
            m1_fwd.close()
            m1_rev.close()
            m2_fwd.close()
            m2_rev.close()
            zero_button_1.close()
            zero_button_2.close()
            print("\nGPIO closed. Goodbye.")
            ser.close()


if __name__ == "__main__":
    main()