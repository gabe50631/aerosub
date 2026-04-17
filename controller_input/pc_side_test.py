import pygame
import socket
import time

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise Exception("No joystick detected")

joystick = pygame.joystick.Joystick(0)
joystick.init()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

target_ip = "192.168.1.50"
target_port = 5005

def normalize(axis):
    # pygame axis is [-1, 1] → convert to [0, 1]
    return (axis + 1) / 2

while True:
    pygame.event.pump()

    raw_axis = joystick.get_axis(0)
    value = normalize(raw_axis)

    # optional: deadzone to reduce noise
    if abs(raw_axis) < 0.05:
        value = 0.5

    # send as float string
    sock.sendto(f"{value:.3f}".encode(), (target_ip, target_port))

    print(f"Sent: {value:.3f}")

    time.sleep(0.2)  # 50 Hz update rate