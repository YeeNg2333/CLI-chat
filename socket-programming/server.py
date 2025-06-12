import socket
import threading
import sys
import json
import time
import os

online_users = {}
lock = threading.Lock()


class User:
    def __init__(self, username, conn, anonymous:bool = False, unread_list:list = None):
        self.anonymous = anonymous
        self.username = username
        self.conn = conn
        self.target = None
        self.unread_list = unread_list
#对所有用户发广播
def broadcast(msg:str , whosend = 'sys'):
    for user in online_users:
        # online_users[user].conn.sendall(msg.encode())
        send_to(online_users[user].conn, {'whosend': whosend, 'msg': msg})

# 传入带有用户对象的列表，并依次发送消息
def groupchat(msg,memberlist = None):
    if memberlist:
        for obj in memberlist:
            # obj.conn.sendall(msg.encode())
            send_to(obj.conn,msg)

# 传入要发送的对象
def send_to(conn:socket.socket, msg:dict = None):
    if type(msg) is not dict:
        raise TypeError('msg must be a dict')
    msgtogo = json.dumps(msg)
    try:
        conn.sendall((msgtogo + '\n').encode())
    except Exception as e:
        print(e)

def writelogs(logtype:str = 'Notype',logmsg:str = '什么都没有？！！'):
    if logmsg:
        nowtime = time.strftime("%Y-%m-%d_%H.%M.%S", time.localtime())
        with open(f'./logs.txt', 'a') as log:
            log.write(f'[{logtype}]'+f'{nowtime}: {logmsg}\n')


#获取所有在线用户
def list_users():
    global online_users
    get_users = []
    for get_user in online_users.keys():
        if online_users[get_user].anonymous:
            continue
        get_users.append(online_users[get_user].username)
    return get_users

def handle_client(conn, addr):
    try:
        username = conn.recv(1024).decode().strip()
        if not username:
            send_to(conn, {'status': 'ERROR'})
            conn.close()
            return

        with lock:
            if username in online_users:
                send_to(conn, {'status': "FAIL"})
                conn.close()
                return
            else:
                try:
                    send_to(conn, {'status': "SUCCESS"})
                    user = User(username, conn)
                    online_users[username] = user
                except Exception as e:
                    print(e)

        print(f"[+] {username} 上线 ({addr[0]}:{addr[1]})")
        broadcast(f"[通知] {username} 上线了")

        while True:
            data = conn.recv(1024).decode().strip()
            if not data: break


            # 进入指令检索
            if data.startswith("/"): # 切换聊天对象命令格式: /switch [target_username]
                if data.startswith("/switch") or data.startswith("/sw "):
                    parts = data.split()
                    if len(parts) < 2:
                        # send_to(conn, "ERROR 未指定用户")
                        send_to(conn, {'whosend':'sys','msg': "ERROR 未指定用户"})
                        continue

                    target = parts[1]
                    with lock:
                        if target in online_users and target != username and online_users[target].anonymous == False:
                            online_users[username].target = target
                            # send_to(conn, f"已切换到 {target}")
                            # conn.sendall(f"已切换到 {target}".encode())
                            send_to(conn, {'whosend': 'sys', 'msg': f"已切换到 {target}", 'target': target})

                        else:
                            # conn.send("ERROR 用户不存在或无法选择自己".encode())
                            send_to(conn, {'whosend': 'sys', 'msg': "ERROR 用户不存在或无法选择自己"})
                elif data.startswith("/list") or data.startswith("/ls"): # 列出在线用户
                    get_list_users = '\n '.join(list_users())
                    # send_to(conn, {'whosend':username,'msg':f"在线用户：\n {get_list_users}")
                    # conn.sendall(f"在线用户：\n {get_list_users}".encode())
                    send_to(conn, {'whosend': 'sys', 'msg': f"在线用户：\n {get_list_users}"})
                elif data.startswith("/select") or data.startswith("/sl"): # 列出在线用户，并进入选择用户模式
                    n = 1
                    # conn.send('在线用户：\n'.encode())
                    send_to(conn, {'whosend': 'sys', 'msg': '在线用户：\n'})
                    # ls_us = '\n '.join(list_users())
                    for i in list_users():
                        # conn.send(f'|({n}) - {list_users()[n-1]}\n'.encode())
                        send_to(conn, {'whosend': 'sys', 'msg': f'|({n}) - {list_users()[n-1]}\n'})
                        n += 1
                    # conn.send('直接输入序号来选择用户'.encode())
                    send_to(conn, {'whosend': 'sys', 'msg': '直接输入序号来选择用户'})
                    data = conn.recv(1024).decode().strip()
                    if not data: break
                    parts = data.split()
                    if len(parts) == 0 or parts[0].isdigit() == False:
                        # conn.send("取消选择".encode())
                        send_to(conn, {'whosend': 'sys', 'msg': "取消选择"})
                        continue
                    # 通过输入数字来得到选择用户（不需要再打名字）
                    try:
                        target_num = int(parts[0])
                        target = list_users()[target_num - 1]
                        with lock:
                            if target in online_users and target != username:
                                online_users[username].target = target
                                # conn.send(f"已切换到 {target}".encode())
                                send_to(conn, {'whosend': 'sys', 'msg': f"已切换到 {target}", 'target': target})
                            else:
                                # conn.sendall("ERROR 用户不存在或无法选择自己 ".encode())
                                # conn.sendall("取消选择".encode())
                                send_to(conn, {'whosend': 'sys', 'msg': "ERROR 用户不存在或无法选择自己\n已取消选择"})

                    except IndexError:
                        # conn.sendall('[错误] 选中序号不存在'.encode())
                        send_to(conn, {'whosend': 'sys', 'msg': '[错误] 选中序号不存在'})
                elif data.startswith("/dive") or data.startswith("/dv"):
                    # conn.sendall('已经切换到潜水模式'.encode())
                    if online_users[username].anonymous == True:
                        online_users[username].anonymous = False
                        send_to(conn, {'whosend': 'sys', 'msg': f'已关闭潜水模式'})
                    elif online_users[username].anonymous == False:
                        online_users[username].anonymous = True
                        send_to(conn, {'whosend': 'sys', 'msg': f'已开启潜水模式'})
                elif data.startswith("/help"):
                    # conn.send('命令集：\nswitch(sw) [username]切换到指定用户\nlist(ls) 列出所有用户\nselect(sl) 列出用户，并提供按序号选择用户\ndive(dv) 潜水！！！'.encode())
                    send_to(conn, {'whosend': 'sys', 'msg': '命令集：\nswitch(sw) [username]切换到指定用户\nlist(ls) 列出所有用户\nselect(sl) 列出用户，并提供按序号选择用户\ndive(dv) 切换潜水开关'})
                else:
                    # conn.send('[错误] 无效指令或不完整的参数，使用/help来查看所有可用的指令及其用法'.encode())
                    send_to(conn, {'whosend': 'sys', 'msg': '[错误] 无效指令或不完整的参数，使用/help来查看所有可用的指令及其用法'})
            # 普通消息转发
            elif user.target:
                with lock:
                    if user.target in online_users:
                        receiver = online_users[user.target] # receiver即目的地用户对象
                        # receiver.conn.send(f"[消息] <{username}> | {data}".encode())
                        send_to(receiver.conn, {'whosend': username, 'msg': data})
                    else:
                        # conn.send(f"[错误] {user.target}已离线".encode())
                        send_to(conn, {'whosend': 'sys', 'msg': f"[错误] {user.target}已离线"})
            else:
                # conn.send("[错误] 未选择聊天对象".encode())
                send_to(conn, {'whosend': 'sys', 'msg': "[错误] 未选择聊天对象"})

    except ConnectionResetError as e:
        print('连接已重置')
        writelogs(logtype='Error',logmsg=f'连接已重置: {str(e)}')
        pass
    except Exception as e:
        print(e)
        # conn.sendall(str(e).encode())
        send_to(conn, {'whosend': 'sys', 'msg': str(e)})
        writelogs(logtype='Error',logmsg=f'发生错误{str(e)}\n')

    finally:
        with lock:
            # if username in online_users:
            #     del online_users[username]
            online_users.pop(username, None)
        conn.close()
        print(f"[-] {username} 离线")
        broadcast(f"[通知] {username} 离线",'sys')


def main():
    if len(sys.argv) != 2:
        print('可选传入参数用法：python server.py [port]')
        port = int(input('输入监听端口：'))
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
        writelogs(logtype='Normal',logmsg='服务器正常关闭.')
        broadcast('[提示] 服务器已下线')
    finally:
        for user in online_users.values():
            # user.conn.sendall('GOODBYE'.encode())
            send_to(user.conn,{'whosend':'sys','msg':'GOODBYE'})
            user.conn.close()
        server.close()


if __name__ == "__main__":
    main()