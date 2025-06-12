import socket
import threading
import sys

online_users = {}
lock = threading.Lock()


class User:
    def __init__(self, username, conn):
        self.username = username
        self.conn = conn
        self.target = None
#对所有用户发广播
def broadcast(msg):
    for user in online_users:
        online_users[user].conn.send(msg.encode())
#获取所有在线用户
def list_users():
    global online_users
    get_users = []
    for get_user in online_users.keys():
        get_users.append(online_users[get_user].username)
    return get_users

def handle_client(conn, addr):
    try:
        username = conn.recv(1024).decode().strip()
        if not username:
            conn.close()
            return

        with lock:
            if username in online_users:
                conn.send("FAIL".encode())
                conn.close()
                return
            else:
                conn.send("SUCCESS".encode())
                user = User(username, conn)
                online_users[username] = user

        print(f"[+] {username} 进入聊天室 ({addr[0]}:{addr[1]})")
        broadcast(f"[通知] {username} 进入聊天室")

        while True:
            data = conn.recv(1024).decode().strip()
            if not data: break


            # 进入指令检索
            if data.startswith("/"): # 切换聊天对象命令格式: /switch [target_username]
                if data.startswith("/switch") or data.startswith("/sw "):
                    parts = data.split()
                    if len(parts) < 2:
                        conn.send("ERROR 未指定用户".encode())
                        continue

                    target = parts[1]
                    with lock:
                        if target in online_users and target != username:
                            online_users[username].target = target
                            conn.send(f"已切换到 {target}".encode())
                        else:
                            conn.send("ERROR 用户不存在或无法选择自己".encode())
                elif data.startswith("/list") or data.startswith("/ls"): # 列出在线用户
                    conn.send(f"在线用户：\n{'\n '.join(list_users())}".encode())
                elif data.startswith("/select") or data.startswith("/sl"): # 列出在线用户，并进入选择用户模式
                    n = 1
                    conn.send('在线用户：'.encode())
                    for i in list_users():
                        conn.send(f' ({n}) - {list_users()[n-1]}\n'.encode())
                        n += 1
                    conn.send('直接输入序号来选择用户'.encode())
                    data = conn.recv(1024).decode().strip()
                    if not data: break
                    parts = data.split()
                    if len(parts) == 0:
                        conn.send("取消选择".encode())
                        continue
                    # 通过输入数字来得到选择用户（不需要再打名字）
                    try:
                        target_num = int(parts[0])
                        target = list_users()[target_num - 1]
                        with lock:
                            if target in online_users and target != username:
                                online_users[username].target = target
                                conn.send(f"已切换到 {target}".encode())
                            else:
                                conn.send("ERROR 用户不存在或无法选择自己".encode())
                                conn.send("取消选择".encode())
                    except IndexError:
                        conn.send('[错误] 选中序号不存在'.encode())
                elif data.startswith("/help"):
                    conn.send('懒得写，自己猜去吧'.encode())
                else:
                    conn.send('无效指令或不完整的参数，使用/help来查看所有可用的指令及其用法'.encode())
            # 普通消息转发
            elif user.target:
                with lock:
                    if user.target in online_users:
                        receiver = online_users[user.target]
                        receiver.conn.send(f"[消息] {username} | {data}".encode())
                    else:
                        conn.send("ERROR 对方已离线".encode())
            else:
                conn.send("ERROR 请先设置聊天对象".encode())

    except ConnectionResetError:
        pass
    finally:
        with lock:
            if username in online_users:
                del online_users[username]
        conn.close()
        print(f"[-] {username} 离线")
        broadcast(f"[通知] {username} 离线")


def main():
    if len(sys.argv) != 2:
        port = input('输入监听端口：')
    else:
        port = int(sys.argv[1])
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', port))
    server.listen(5)
    print(f"[*] 服务端在端口 {port} 监听中...")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()
    except KeyboardInterrupt:
        print("\n[!] 服务端关闭")
        broadcast('[提示] 服务器已下线')
    finally:
        server.close()


if __name__ == "__main__":
    main()