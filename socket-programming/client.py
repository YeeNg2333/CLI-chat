import socket
import threading
import sys
import json

current_target = None # 聊天发送对象

def receive_messages(conn):
    global current_target
    while True:
        try:
            # data = conn.recv(1024).decode()
            data = receive_responses(conn)
            if not data or 'GOODBYE' in data.get('msg'):
                assert 'GOODBYE' in data.get('msg'),'GOOD BYE'
                break
            # print("\r" + data + "\n> ", end="")
            assert data.get('status') != 'JSONDecodeError','JSONDecodeError'
            if 'target' in data.keys():
                # current_target = data.split()[1] if len(data.split()) > 1 else None
                current_target = data.get('target')
            if data.get('whosend') == 'sys':
                if current_target:
                    print("\r " + data.get('msg') + '\n' + current_target + '> ', end="")
                else:
                    print("\r " + data.get('msg') + '\n' + '> ', end="")
            else:
                if current_target:
                    print("\r " + '<' + data.get("whosend") + '>' + ' | ' + data.get("msg") + '\n' + current_target + '> ', end="")
                else:
                    print("\r " + data.get('msg') + '\n' + '> ', end="")


            # 获取提示符要显示的聊天对象

        except AssertionError as e:
            print(e)
            break
        except Exception as e:
            print('发生错误：')
            print(e)
            break
        # finally:
        #     break
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


def main(is_first_boot, host = None, port = None):

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

        # print(response)

        try:
            if response.get('status') != "SUCCESS":
                # print("用户名已存在，连接关闭")
                # client.close()
                # return
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
                elif response.get('status') == 'KICK':
                    print('错误次数过多，请稍后重试。')
                    return
                elif response.get('status') is None:
                    print('ERROR 状态位为空')
                else:
                    print(response)
                    raise Exception(response)
            else:
                break
        except Exception as e:
            print(e)

    print(f"\f {username}，Ciallo～(∠・ω< )⌒★\t (输入/help查看命令大全)")

    # 启动接收消息线程
    recv_thread = threading.Thread(target=receive_messages, args=(client,))
    recv_thread.daemon = False
    recv_thread.start()

    global current_target
    try:
        while True:
            if current_target is None: # 不太好用
                print(' ',end='')
            else:
                print(current_target,end='')
            print("> ", end="")
            message = input().strip()

            if not message:
                continue

            # if message.startswith("/switch") or message.startswith("/sw"): # 不再需要
            #     client.send(message.encode())
            #     current_target = message.split()[1] if len(message.split()) > 1 else None

            if message == "/exit":
                break
            else:
                client.send(message.encode())
    # except ConnectionResetError:
    #     print('='*30,'FATAL_ERROR 连接已重置。','='*30,sep='\n')
    #     if input('\t重连服务器？y/n').upper() == "Y":
    #         main(False,host,port)
    except KeyboardInterrupt:
        print('GOOD BYE!')
    # except Exception as e:
    #     print('='*30,'FATAL_ERROR 未知错误\n ',e,'='*30,sep='\n')
    #     if ISFIRSTBOOT is False:
    #         client.close()
    #         return
    #     if input('\t重连服务器？y/n').upper() == "Y":
    #         main(False,host,port)
    finally:
        client.close()
        print("[-] 已断开连接")


if __name__ == "__main__":
    main(is_first_boot= True)
