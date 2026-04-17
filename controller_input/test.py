import pygame

pygame.init()
pygame.joystick.init()

# Check for joystick
if pygame.joystick.get_count() == 0:
    print("No joystick detected")
    exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"Connected to: {joystick.get_name()}")

while True:
    pygame.event.pump()  # Process events

    # Read axes (sticks)
    axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]

    # Read buttons (switches)
    buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]

    print("Axes:", axes)
    print("Buttons:", buttons)

    pygame.time.wait(500)