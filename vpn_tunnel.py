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
        cursor.execute(
            "SELECT password, hash_type FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()

        if row is None:
            return False

        stored_password, hash_type = row

        if hash_type is None or hash_type.lower() == "plain":
            return password == stored_password

        if hash_type.lower() == "sha256":
            password_to_check = hashlib.sha256(password.encode()).hexdigest()
            return password_to_check == stored_password

        print(f"Неизвестный тип хеша у пользователя {username}: {hash_type}")
        return False

    except sqlite3.Error as e:
        print(f"Ошибка БД при проверке пользователя: {e}")
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
            print(f"Ошибка tun2udp: {e}")
            break


def udp2tun(tun_fd, udp_sock, remote_addr):
    while True:
        try:
            data, addr = udp_sock.recvfrom(4096)

            if addr != remote_addr:
                continue

            if data.startswith(b"{"):
                continue

            dec = xor_encrypt(data)
            os.write(tun_fd, dec)
        except Exception as e:
            print(f"Ошибка udp2tun: {e}")
            break


def server_mode():
    tun = create_tun("tun0")
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("0.0.0.0", PORT))

    print(f"Сервер ожидает подключение и авторизацию на порту {PORT}...")

    auth_payload, client_addr = recv_json(udp_sock)

    if auth_payload.get("type") != "auth":
        send_json(udp_sock, client_addr, {"type": "auth_result", "status": "fail", "message": "Неверный тип пакета"})
        print(f"Отклонено подключение от {client_addr}: неверный стартовый пакет")
        return

    username = auth_payload.get("username", "")
    password = auth_payload.get("password", "")

    if verify_user(username, password):
        send_json(udp_sock, client_addr, {"type": "auth_result", "status": "ok", "message": "Авторизация успешна"})
        print(f"Пользователь '{username}' успешно авторизован. Запуск туннеля с {client_addr}")
        remote = client_addr
    else:
        send_json(udp_sock, client_addr, {"type": "auth_result", "status": "fail", "message": "Неверный логин или пароль"})
        print(f"Ошибка авторизации от {client_addr}, пользователь '{username}'")
        return

    t1 = threading.Thread(target=tun2udp, args=(tun, udp_sock, remote), daemon=True)
    t2 = threading.Thread(target=udp2tun, args=(tun, udp_sock, remote), daemon=True)

    t1.start()
    t2.start()
    t1.join()


def client_mode(server_ip):
    tun = create_tun("tun0")
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_addr = (server_ip, PORT)

    print(f"Подключение к серверу {server_ip}:{PORT}")
    username = input("Логин: ")
    password = getpass.getpass("Пароль: ")

    send_json(udp_sock, server_addr, {
        "type": "auth",
        "username": username,
        "password": password
    })

    response, addr = recv_json(udp_sock)

    if addr != server_addr:
        print("Получен ответ не от того сервера")
        return

    if response.get("type") != "auth_result":
        print("Неверный ответ от сервера")
        return

    if response.get("status") != "ok":
        print(f"Авторизация не пройдена: {response.get('message')}")
        return

    print("Авторизация успешна. Туннель запущен.")

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