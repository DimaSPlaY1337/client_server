import os
import sys
import struct
import fcntl
import socket
import threading

TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001

def create_tun(name="tun0"):
    tun = os.open("/dev/net/tun", os.O_RDWR)
    ifr = struct.pack('16sH', name.encode(), IFF_TUN)
    fcntl.ioctl(tun, TUNSETIFF, ifr)
    return tun

def xor_encrypt(data, key=0x5A):
    return bytes(b ^ key for b in data)

def tun2udp(tun_fd, udp_sock, remote_addr, mode):
    while True:
        packet = os.read(tun_fd, 2048)
        if not packet:
            break
        enc = xor_encrypt(packet)
        udp_sock.sendto(enc, remote_addr)

def udp2tun(tun_fd, udp_sock, mode):
    while True:
        data, _ = udp_sock.recvfrom(4096)
        dec = xor_encrypt(data)
        os.write(tun_fd, dec)

def main():
    PORT = 1194
    
    tun = create_tun("tun0")
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    is_server = len(sys.argv) == 1
    
    if is_server:
        print(f"Ожидание подключения на порту {PORT}...")
        udp_sock.bind(("0.0.0.0", PORT))
        _, client_addr = udp_sock.recvfrom(1024)
        udp_sock.sendto(b"\x00", client_addr) # ACK
        remote = client_addr
        mode = "server"
    else:
        remote_IP = sys.argv[1]
        print(f"Подключение к серверу {remote_IP}:{PORT}...")
        udp_sock.sendto(b"\x01", (remote_IP, PORT)) # CH
        udp_sock.recv(1024)
        remote = (remote_IP, PORT)
        mode = "client"

    print(f"Связь установлена с {remote}. Режим: {mode}. Запуск туннеля...")

    # Создание потоков в соответствии с последней фотографией
    t1 = threading.Thread(
        target=tun2udp, 
        args=(tun, udp_sock, remote, mode), 
        daemon=True
    )
    
    t2 = threading.Thread(
        target=udp2tun, 
        args=(tun, udp_sock, mode), 
        daemon=True
    )
    
    t1.start()
    t2.start()
    
    t1.join()

if __name__ == "__main__":
    main()