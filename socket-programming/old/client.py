import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
    client.connect((input('Input server address'), 25565))
    client.sendall(b'Hello, server!')
    data = client.recv(1024)
    print(data)