import socket

def login(host, port, username, password):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, port))
        
        # Склеиваем и отправляем
        credentials = f"{username}:{password}"
        client_socket.send(credentials.encode('utf-8'))
        
        # Получаем вердикт
        response = client_socket.recv(1024).decode('utf-8')
        print(f"\nОтвет от сервера: {response}")
        
    except ConnectionRefusedError:
        print("\nОшибка: Не удалось подключиться к серверу авторизации.")
    finally:
        client_socket.close()

if __name__ == "__main__":
    # Если тестируете на одной машине, оставляйте 127.0.0.1
    server_ip = input("IP сервера (по умолчанию 127.0.0.1): ") or '127.0.0.1'
    port = 8888
    
    print("--- Система сетевой авторизации ---")
    user = input("Логин: ")
    pwd = input("Пароль: ")
    
    login(server_ip, port, user, pwd)