import socket

HOST = "0.0.0.0"
PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))

print(f"Servidor UDP escuchando en {HOST}:{PORT}")

try:
    while True:
        data, address = sock.recvfrom(1024)

        print(
            f"Recibido desde {address}: "
            f"{data.decode('utf-8')}"
        )

except KeyboardInterrupt:
    print("\nServidor detenido por el usuario.")

finally:
    sock.close()
