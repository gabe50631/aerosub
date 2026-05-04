import serial

ser = serial.Serial('/dev/ttyS5', baudrate=9600, timeout=1)

print("Enter 4 integers separated by spaces (e.g. 1 2 3 4)")

while True:
    try:
        user_input = input("Enter 4 integers: ")
        parts = user_input.strip().split()

        if len(parts) != 4:
            print("Please enter exactly 4 integers.")
            continue

        values = [int(x) for x in parts]

        # Send as CSV line
        message = "{},{},{},{}\n".format(*values)
        ser.write(message.encode('utf-8'))

        print(f"Sent: {values}")

    except ValueError:
        print("Invalid input. Use integers only.")
    except KeyboardInterrupt:
        print("\nExiting.")
        break

ser.close()