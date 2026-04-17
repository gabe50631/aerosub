from periphery import GPIO
import time

ZERO_BUTTON_PIN = 52    # Pushbutton for homing/zeroing

# Initialize GPIO pin as input
button = GPIO(ZERO_BUTTON_PIN, "in")

try:
    print("Button Test Running... Press Ctrl+C to exit")
    while True:
        button_state = button.read()
        if button_state:
            print("Button is ON  (Pressed)")
        else:
            print("Button is OFF (Released)")
        time.sleep(0.1)  # Small delay to avoid flooding the terminal

except KeyboardInterrupt:
    print("\nTest stopped by user")

finally:
    button.close()
    print("GPIO cleaned up")