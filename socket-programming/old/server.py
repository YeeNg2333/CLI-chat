import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.bind(('0.0.0.0', 25565))
    server.listen()
    client, addr = server.accept()
    with client:
        print('Connected.', addr)
        while True:
            try:
                data = client.recv(1024)
            except Exception as e:
                print(e)
            if not data:
                break
            client.sendall(data)