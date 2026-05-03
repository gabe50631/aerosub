# -----Joystick Naming-----
# left joystick horizontal = ljx
# left joystick vertical = ljy
# right joystick horizontal = rjx
# right joystick vertical = rjy
# right trigger = rt

import pygame
import socket
import time
import struct

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    raise Exception("No joystick detected")

joystick = pygame.joystick.Joystick(0)
joystick.init()

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

target_ip = "192.168.1.50"
target_port = 5005

while True:
    pygame.event.pump()

    rjx = joystick.get_axis(0)
    rjy = joystick.get_axis(1)
    ljy = joystick.get_axis(2)
    ljx = joystick.get_axis(3)
    rt = joystick.get_axis(5)

    axes_data = struct.pack("5f", rjx, rjy, ljy, ljx, rt)
    sock.sendto(axes_data, (target_ip, target_port))

    print(f"Sent rjx: {rjx:.3f} rjy: {rjy:.3f} ljy: {ljy:.3f} ljx: {ljx:.3f} rt: {rt:.3f}")

    time.sleep(0.02)  # 50 Hz update rate