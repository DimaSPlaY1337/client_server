import socket
import sqlite3
import hashlib

DB_PATH = 'db.sqlite'

def verify_credentials(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def start_server(host='0.0.0.0', port=8888):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Позволяем переиспользовать адрес, чтобы не было ошибки "Address already in use"
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Сервер сетевой авторизации запущен на {host}:{port}...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Попытка подключения от {addr}")
        
        try:
            # Ожидаем пакет вида "логин:пароль"
            data = client_socket.recv(1024).decode('utf-8').strip()
            
            if not data or ':' not in data:
                client_socket.send("ОШИБКА: Неверный формат".encode('utf-8'))
                client_socket.close()
                continue
                
            username, password = data.split(':', 1)
            
            # Сверяем с БД
            if verify_credentials(username, password):
                client_socket.send("200 УСПЕХ: Авторизация пройдена".encode('utf-8'))
                print(f"[OK] Пользователь '{username}' успешно авторизован.")
            else:
                client_socket.send("403 ОТКАЗ: Неверные учетные данные".encode('utf-8'))
                print(f"[FAIL] Отказ для пользователя '{username}'.")
                
        except Exception as e:
            print(f"Ошибка при обработке клиента: {e}")
        finally:
            client_socket.close()

if __name__ == "__main__":
    start_server()