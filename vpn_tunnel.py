import os
import sys
import struct
import fcntl
import socket
import threading
import sqlite3
import hashlib
import json
import getpass

TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001

PORT = 1194
DB_PATH = "db.sqlite"
XOR_KEY = 0x5A

def create_tun(name="tun0"):
    tun = os.open("/dev/net/tun", os.O_RDWR)
    ifr = struct.pack("16sH", name.encode(), IFF_TUN)
    fcntl.ioctl(tun, TUNSETIFF, ifr)
    
    # Автоматически поднимаем интерфейс, чтобы избежать ошибки Errno 5
    os.system(f"ip link set dev {name} up")
    
    return tun

def xor_encrypt(data, key=XOR_KEY):
    return bytes(b ^ key for b in data)

def verify_user(username, password):
    if not os.path.exists(DB_PATH):
        print(f"База данных не найдена: {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT password, hash_type FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if row is None:
            return False

        stored_password, hash_type = row

        if hash_type is None or hash_type.lower() == "plain":
            return password == stored_password

        if hash_type.lower() == "sha256":
            password_to_check = hashlib.sha256(password.encode()).hexdigest()
            return password_to_check == stored_password

        return False

    except sqlite3.Error as e:
        print(f"Ошибка БД: {e}")
        return False
    finally:
        conn.close()

def send_json(sock, addr, payload):
    data = json.dumps(payload).encode("utf-8")
    sock.sendto(data, addr)

def recv_json(sock, bufsize=4096):
    data, addr = sock.recvfrom(bufsize)
    payload = json.loads(data.decode("utf-8"))
    return payload, addr

def tun2udp(tun_fd, udp_sock, remote_addr):
    while True:
        try:
            packet = os.read(tun_fd, 2048)
            if not packet:
                break
            enc = xor_encrypt(packet)
            udp_sock.sendto(enc, remote_addr)
        except Exception as e:
            print(f"Туннель закрыт (tun2udp): {e}")
            break

def udp2tun(tun_fd, udp_sock, remote_addr):
    while True:
        try:
            data, addr = udp_sock.recvfrom(4096)
            if addr != remote_addr or data.startswith(b"{"):
                continue
            dec = xor_encrypt(data)
            os.write(tun_fd, dec)
        except Exception as e:
            print(f"Туннель закрыт (udp2tun): {e}")
            break

def server_mode():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("0.0.0.0", PORT))
    print(f"Сервер ожидает авторизацию на порту {PORT}...")

    auth_payload, client_addr = recv_json(udp_sock)
    
    username = auth_payload.get("username", "")
    password = auth_payload.get("password", "")

    if verify_user(username, password):
        send_json(udp_sock, client_addr, {"type": "auth_result", "status": "ok"})
        print(f"[+] Пользователь '{username}' авторизован. Поднимаем tun0...")
        
        # Создаем tun0 только после успеха
        tun = create_tun("tun0")
        
        t1 = threading.Thread(target=tun2udp, args=(tun, udp_sock, client_addr), daemon=True)
        t2 = threading.Thread(target=udp2tun, args=(tun, udp_sock, client_addr), daemon=True)
        t1.start()
        t2.start()
        t1.join()
    else:
        send_json(udp_sock, client_addr, {"type": "auth_result", "status": "fail"})
        print(f"[-] Ошибка авторизации от {client_addr} для '{username}'")

def client_mode(server_ip):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Добавляем таймаут, чтобы клиент не висел вечно, если сервер не отвечает
    udp_sock.settimeout(5.0) 
    server_addr = (server_ip, PORT)

    print(f"Подключение к серверу {server_ip}:{PORT}")
    username = input("Логин: ")
    password = getpass.getpass("Пароль: ")

    try:
        send_json(udp_sock, server_addr, {"type": "auth", "username": username, "password": password})
        response, addr = recv_json(udp_sock)
    except socket.timeout:
        print("Ошибка: Сервер не ответил (таймаут).")
        return

    if response.get("status") != "ok":
        print("Авторизация не пройдена: неверный логин или пароль.")
        return

    print("[+] Авторизация успешна! Поднимаем tun1...")
    
    # Отключаем таймаут для нормальной работы туннеля
    udp_sock.settimeout(None)
    
    # КЛИЕНТ ТЕПЕРЬ ИСПОЛЬЗУЕТ tun1
    tun = create_tun("tun1")

    t1 = threading.Thread(target=tun2udp, args=(tun, udp_sock, server_addr), daemon=True)
    t2 = threading.Thread(target=udp2tun, args=(tun, udp_sock, server_addr), daemon=True)
    t1.start()
    t2.start()
    t1.join()

def main():
    is_server = len(sys.argv) == 1
    if is_server:
        server_mode()
    else:
        server_ip = sys.argv[1]
        client_mode(server_ip)

if __name__ == "__main__":
    main()