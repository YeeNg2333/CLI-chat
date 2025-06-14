import socket
import threading
import sys
import json
import time

current_target = None # 聊天发送对象
thread_keep_running = True

class Client:
    def __init__(self, conn:socket.socket, username:str):
        self.conn = conn
        self.username = username

    def send_to(self, msg_dict:dict, is_command = False):
        if type(msg_dict) is not dict:
            raise TypeError('msg must be a dict')
        msg_dict['cmd'] = is_command
        msg_to_go = json.dumps(msg_dict)
        try:
            self.conn.sendall((msg_to_go + '\n').encode())
        except Exception as e:
            print(e)
            return


# 这是一个线程
def receive_messages(conn:socket.socket,keep_running:bool = True):
    global current_target
    while True:
        try:
            # data = conn.recv(1024).decode()
            data = receive_responses(conn)
            if not data or data.get('msg') == 'GOODBYE':
                assert 'GOODBYE' in data.get('msg'),'GOODBYE'
                break
            # print("\r" + data.get('msg') + "\n> ", end="")
            # print(data)
            assert data.get('status') != 'JSONDecodeError','JSONDecodeError'
            if 'target' in data.keys():# 获取聊天对象
                # current_target = data.split()[1] if len(data.split()) > 1 else None
                current_target = data.get('target')
            if data.get('whosend') == 'sys':# 判别是否为系统通知
                print("\r " + data.get('msg'))
            else:
                print("\r " + '<' + data.get("whosend") + '>' + ' | ' + data.get("msg"))
            print_prompt()

        except AssertionError as e:
            if not keep_running: break
            else: print(e)
            break
        except Exception as e:
            if not keep_running: break
            print('\r【警告】收到消息时发生错误：')
            print(e)
            if input('是否继续？y/n :') == 'y': continue
            else: break
        # finally:
        #     print_prompt()
# 接收json格式的消息，遇到换行符结束
def receive_responses(conn):
    buffer = b''
    while True:
        # 尝试接收数据直到遇到换行符
        chunk = conn.recv(1)
        if not chunk:
            break
        buffer += chunk
        if buffer.endswith(b'\n'):
            break
    # 去除换行符并解析
    json_str = buffer[:-1].decode()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # print('JSONDecodeError')
        return {'status':'JSONDecodeError'}

def print_prompt():
    global current_target
    print(current_target if current_target is not None else '', end= '')
    print('> ', end= '',flush=True)

def main(is_first_boot, host = None, port = None):
    global thread_keep_running
    if is_first_boot: # 判断是否为递归调用
        if len(sys.argv) != 3:
            print("可选传入参数的用法: python client.py <服务器IP> <端口>")
            host = input('输入服务器IP：')
            port = int(input('输入服务器端口：'))
            # print("用法: python client.py <服务器IP> <端口>")
            # return
        else:
            host = sys.argv[1]
            port = int(sys.argv[2])
        # host = sys.argv[1]
        # port = int(sys.argv[2])

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((host, port))
    except Exception as e:
        print(f"[!] 无法连接到服务器: {e}")
        return

    username = input("请输入用户名: ")
    # 判别输入用户名
    while True: # 使用frp时会遇到字节流粘连问题
        client.send(username.encode())
        # response = client.recv(1024).decode() # 隧道连接会卡住
        response:dict = receive_responses(client)

        print(response)

        try:
            if response.get('status') != "SUCCESS":
                if response.get('status') == 'FAIL':
                    print('重复的用户名。')
                    return
                    # username = input("请输入用户名: ")
                    # client.send(username.encode())
                elif response.get('status') == 'EMPTY':
                    print('用户名为空！')
                    return
                    # username = input("请输入用户名: ")
                    # client.send(username.encode())
                # elif response.get('status') == 'KICK':
                #     print('错误次数过多，请稍后重试。')
                #     return
                elif response.get('status') is None:
                    print('ERROR 状态位为空')
                    return
                else:
                    print(response)
                    raise Exception(response)
            else:
                break
        except Exception as e:
            print(e)

    print('[√] 认证通过')

    # 启动接收消息线程

    recv_thread = threading.Thread(target=receive_messages, args=(client,thread_keep_running,))
    recv_thread.daemon = False
    recv_thread.start()

    global current_target
    server_now = Client(client,username)
    try:
        while True:
            print_prompt()
            message = input().strip()

            if not message:
                continue

            # if message.startswith("/switch") or message.startswith("/sw"): # 不再需要
            #     client.send(message.encode())
            #     current_target = message.split()[1] if len(message.split()) > 1 else None

            if message.startswith('/'): # 进入命令处理
                if message.startswith('/exit'):
                    server_now.send_to({'msg':message},True)
                    exit(0)
                server_now.send_to({'msg':message},True)

            else:
                server_now.send_to({'msg': message})

    # except ConnectionResetError:
    #     print('='*30,'FATAL_ERROR 连接已重置。','='*30,sep='\n')
    #     if input('\t重连服务器？y/n').upper() == "Y":
    #         main(False,host,port)
    except KeyboardInterrupt:
        print('GOODBYE!')
        server_now.send_to({'msg': '/exit'}, True)
    # except Exception as e:
    #     print('='*30,'FATAL_ERROR 未知错误\n ',e,'='*30,sep='\n')
    #     if ISFIRSTBOOT is False:
    #         client.close()
    #         return
    #     if input('\t重连服务器？y/n').upper() == "Y":
    #         main(False,host,port)
    finally:
        thread_keep_running = False
        time.sleep(1)
        client.close()
        print("[-] 已断开连接")
        exit()


if __name__ == "__main__":
    main(is_first_boot= True)
