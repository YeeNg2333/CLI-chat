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

    # 传入要发送的对象，集成在用户对象后，不需要再传入conn，因为可以直接调用conn
    # 作为该对象里的行为，给自己的客户端发送信息。
    def send_to(self, msg: dict = None):
        if type(msg) is not dict:
            raise TypeError('msg must be a dict')
        msg_to_go = json.dumps(msg)
        try:
            self.conn.sendall((msg_to_go + '\n').encode())
        except Exception as e:
            print(e)

    # 接收json格式的消息，遇到换行符结束
    def receive_responses(self):
        buffer = b''
        while True:
            # 尝试接收数据直到遇到换行符
            chunk = self.conn.recv(1)
            if not chunk:
                break
            buffer += chunk
            if buffer.endswith(b'\n'):
                break
        # 去除换行符并解析
        json_str = buffer[:-1].decode()
        try:
            print(json_str)
            return json.loads(json_str)
        except json.JSONDecodeError:
            # print('JSONDecodeError')
            return {'status': 'JSONDecodeError'}

# 对所有用户发广播，
# 在这个分支里，这个要怎么解决？
def broadcast(msg:str , whosend = 'sys'):
    for user in online_users:
        # online_users[user].conn.sendall(msg.encode())
        online_users[user].send_to({'whosend': whosend, 'msg': msg})

# 传入带有用户对象的列表，并依次发送消息
def group_chat(msg, member_list = None):
    if member_list:
        for obj in member_list:
            # obj.conn.sendall(msg.encode())
            obj.send_to(msg)

# 传入要发送的对象
# 已经移入user里

# 记录，打印日志并且写入日志文件里
def write_logs(log_type:str = 'Notype', log_msg:str = '什么都没有？！！'):
    if log_msg:
        nowtime = time.strftime("%Y-%m-%d_%H.%M.%S", time.localtime())
        the_log_string = (f'[{log_type}]' + f'{nowtime}: {log_msg}\n')
        with open(f'./logs.txt', 'a', encoding='utf-8') as log:
            print(the_log_string)
            log.write(the_log_string)


#获取所有在线用户
def list_users():
    global online_users
    get_users = []
    for get_user in online_users.keys():
        if online_users[get_user].anonymous:
            continue
        get_users.append(online_users[get_user].username)
    return get_users

def create_user(conn, addr):
    global online_users
    def send_to(self, msg: dict = None):
        if type(msg) is not dict:
            raise TypeError('msg must be a dict')
        msg_to_go = json.dumps(msg)
        try:
            conn.sendall((msg_to_go + '\n').encode())
        except Exception as e:
            print(e)

    try:
        username = conn.recv(1024).decode().strip() #建立连接后，客户端询问用户名
        if not username: #用户名为空的解决办法
            send_to(conn, {'status': 'ERROR'})
            conn.close()
            return

        with lock:
            if username in online_users: # 检测到重复用户名，断开连接
                username = None
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
        # 用户名检查没有问题
        print(f"[+] {username} 上线 ({addr[0]}:{addr[1]})")
        handle_client(user, username)

    except ConnectionResetError as e:
        print('连接已重置')
        write_logs(log_type='Error', log_msg=f'连接已重置: {str(e)}')
        pass
    except Exception as e:
        print(e)
        # conn.sendall(str(e).encode())
        user.send_to({'whosend': 'sys', 'msg': str(e)})
        write_logs(log_type='Error', log_msg=f'发生错误{str(e)}\n')

    finally:
        with lock:
            # if username in online_users:
            #     del online_users[username]
            if username:
                if username in online_users:
                    online_users.pop(username, None)
                    print(f"[-] {username} 离线")
                    broadcast(f"[通知] {username} 离线", 'sys')
        conn.close()

def handle_client(user, username):

    broadcast(f"[通知] {username} 上线了")
    try:
        while True:
            # data = user.conn.recv(1024).decode().strip()
            data = user.receive_responses()
            if not data: break


            # 进入指令检索
            if data.get('cmd'): # 切换聊天对象命令格式: /switch [target_username]
                command = data.get('msg')
                parts = command.split()
                # if data.startswith("/switch") or data.startswith("/sw "):
                def command_is(command_full:str,command_simp:str = None):
                    if parts[0][1:] == command_full or parts[0][1:] == command_simp:
                        return True
                    else:
                        return False
                if command_is('switch','sw'):
                    try:
                        target = parts[1]
                        with lock:
                            if target in online_users and target != username and online_users[target].anonymous == False:
                                online_users[username].target = target
                                # send_to(conn, f"已切换到 {target}")
                                user.send_to({'whosend': 'sys', 'msg': f"已切换到 {target}", 'target': target})
                            else:
                                # conn.send("ERROR 用户不存在或无法选择自己".encode())
                                user.send_to({'whosend': 'sys', 'msg': "ERROR 用户不存在或无法选择自己"})
                    except IndexError:
                        if len(parts) < 2:
                            user.send_to({'whosend': 'sys', 'msg': "ERROR 未指定用户"})
                elif command_is('list','ls'): # 列出在线用户
                    get_list_users = '\n '.join(list_users())
                    # send_to(conn, {'whosend':username,'msg':f"在线用户：\n {get_list_users}")
                    user.send_to({'whosend': 'sys', 'msg': f"在线用户：\n {get_list_users}"})
                elif command_is('select','sl'): # 列出在线用户，并进入选择用户模式
                    n = 1
                    # conn.send('在线用户：\n'.encode())
                    user.send_to({'whosend': 'sys', 'msg': '在线用户：\n'})
                    # ls_us = '\n '.join(list_users())
                    for i in list_users():
                        # conn.send(f'|({n}) - {list_users()[n-1]}\n'.encode())
                        user.send_to({'whosend': 'sys', 'msg': f'|({n}) - {list_users()[n-1]}\n'})
                        n += 1
                    # conn.send('直接输入序号来选择用户'.encode())
                    user.send_to({'whosend': 'sys', 'msg': '直接输入序号来选择用户'})
                    data = user.receive_responses()
                    if not data: break
                    if data is None or data['msg'].isdigit() == False:
                        # conn.send("取消选择".encode())
                        user.send_to({'whosend': 'sys', 'msg': "取消选择"})
                        continue
                    # 通过输入数字来得到选择用户（不需要再打名字）
                    try:
                        target_num = int(data['msg'])
                        target = list_users()[target_num - 1]
                        with lock:
                            if target in online_users and target != username:
                                online_users[username].target = target
                                # conn.send(f"已切换到 {target}".encode())
                                user.send_to({'whosend': 'sys', 'msg': f"已切换到 {target}", 'target': target})
                            else:
                                # conn.sendall("ERROR 用户不存在或无法选择自己 ".encode())
                                # conn.sendall("取消选择".encode())
                                user.send_to({'whosend': 'sys', 'msg': "ERROR 用户不存在或无法选择自己\n已取消选择"})

                    except IndexError:
                        # conn.sendall('[错误] 选中序号不存在'.encode())
                        user.send_to({'whosend': 'sys', 'msg': '[错误] 选中序号不存在'})
                elif command_is('dive','dv'):
                    # conn.sendall('已经切换到潜水模式'.encode())
                    if online_users[username].anonymous:
                        online_users[username].anonymous = False
                        user.send_to({'whosend': 'sys', 'msg': f'已关闭潜水模式'})
                    elif not online_users[username].anonymous:
                        online_users[username].anonymous = True
                        user.send_to({'whosend': 'sys', 'msg': f'已开启潜水模式'})
                elif command_is('help'):
                    # conn.send('命令集：\nswitch(sw) [username]切换到指定用户\nlist(ls) 列出所有用户\nselect(sl) 列出用户，并提供按序号选择用户\ndive(dv) 潜水！！！'.encode())
                    user.send_to({'whosend': 'sys', 'msg': '命令集：\nswitch(sw) [username]切换到指定用户\nlist(ls) 列出所有用户\nselect(sl) 列出用户，并提供按序号选择用户\ndive(dv) 切换潜水开关'})
                else:
                    # conn.send('[错误] 无效指令或不完整的参数，使用/help来查看所有可用的指令及其用法'.encode())
                    user.send_to({'whosend': 'sys', 'msg': '[错误] 无效指令或不完整的参数，使用/help来查看所有可用的指令及其用法'})
            # 普通消息转发
            elif user.target:
                with lock:
                    if user.target in online_users:
                        receiver = online_users[user.target] # receiver即目的地用户对象
                        # receiver.conn.send(f"[消息] <{username}> | {data}".encode())
                        user.send_to(receiver.conn, {'whosend': username, 'msg': data})
                    else:
                        # conn.send(f"[错误] {user.target}已离线".encode())
                        user.send_to({'whosend': 'sys', 'msg': f"[错误] {user.target}已离线"})
            else:
                # conn.send("[错误] 未选择聊天对象".encode())
                user.send_to({'whosend': 'sys', 'msg': "[错误] 未选择聊天对象"})
    # 在这个块里，还需要吗？
    except ConnectionResetError as e:
        print('连接已重置')
        write_logs(log_type='Error', log_msg=f'连接已重置: {str(e)}')
        pass
    except Exception as e:
        print(e)
        # conn.sendall(str(e).encode())
        user.send_to({'whosend': 'sys', 'msg': str(e)})
        write_logs(log_type='Error', log_msg=f'发生错误{str(e)}\n')

    finally:
        with lock:
            # if username in online_users:
            #     del online_users[username]
            if username:
                if username in online_users:
                    online_users.pop(username, None)
                    print(f"[-] {username} 离线")
                    broadcast(f"[通知] {username} 离线", 'sys')
        user.conn.close()


def main():
    if len(sys.argv) != 2:
        print('可选传入参数用法：python server.py [port]')
        port = int(input('输入监听端口：'))
    else:
        port = int(sys.argv[1])
    not_success = True
    tried = 0 # 下面这个块的尝试次数
    while not_success:
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(('0.0.0.0', port))
            server.listen(5)
            print(f"[*] 服务端在端口 【{port}】 监听中...")
            not_success = False
        except socket.error as e:
            write_logs('Warn', f'第 【{tried}】 次出现异常，端口被占用: ' + str(e))
            time.sleep(3)
            tried += 1
            if tried > 5:
                write_logs('Error', f'尝试在【{port}】端口创建监听失败' + str(e))

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=create_user, args=(conn, addr))
            thread.daemon = True
            thread.start()
    except KeyboardInterrupt:
        print("\n[!] 服务端关闭")
        write_logs(log_type='Normal', log_msg='服务器正常关闭.')
        broadcast('[提示] 服务器已下线')
    finally:
        for user in online_users.values():
            # user.conn.sendall('GOODBYE'.encode())
            user.send_to({'whosend':'sys','msg':'GOODBYE'})
            user.conn.close()
        server.close()

# 那很经典了
if __name__ == "__main__":
    main()