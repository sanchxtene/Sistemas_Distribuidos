from print_cliente import imprimir_retorno
import threading
import signal
import sys
import queue
import socket

running = True

acks  = {}
historico = {}
lock = threading.Lock()

# fila de pedidos de retransmissão
retransmit_queue = queue.Queue()

client_sock = None
server_addr_global = None
server_port_global = None

def handle_sigint(sig, frame):
    global running
    print("\nEncerrando cliente...")
    running = False
    try:
        if client_sock:
            client_sock.sendto(b"EXIT", (server_addr_global, server_port_global))
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)


def processar_retransmissoes(sock, server_addr, server_port):
    """
    Executado pelo input_thread.
    Processa pedidos de reenvio vindos da receive_thread.
    """
    while not retransmit_queue.empty():

        faltante = retransmit_queue.get()

        with lock:
            msg = historico.get(faltante)

        if msg:
            sock.sendto(msg.encode(), (server_addr, server_port))


def enviar_com_timeout(sock, server_addr, server_port, req_id, numero):
    mensagem = f"{req_id}|{numero}"

    evento = threading.Event()

    with lock:
        acks[req_id] = evento
        historico[req_id] = mensagem

    MAX_RETRIES = 3

    for tentativa in range(MAX_RETRIES):
        sock.sendto(mensagem.encode(), (server_addr, server_port))

        if evento.wait(timeout=0.01):
            with lock:
                acks.pop(req_id,None)
            return True

    print("Servidor indisponível.")
    return False


def input_thread(sock, server_addr, server_port, caminho_arquivo):
    global running
    req_id = 0

    try:
        with open(caminho_arquivo) as f:
            for linha in f:
                if not running:
                    break

                # antes de nova requisição,
                # verifica se servidor pediu reenvio
                processar_retransmissoes(sock, server_addr, server_port)

                linha = linha.strip()

                if not linha:
                    continue

                numero = int(linha)
                req_id += 1

                ok = enviar_com_timeout(sock, server_addr, server_port, req_id, numero)

                if not ok:
                    running = False
                    break

            print("\nEOF recebido. Encerrando...")
            sock.sendto(b"EXIT", (server_addr, server_port))
            running = False
    
    except EOFError:
        print("\nEOF recebido. Encerrando...")
        sock.sendto(b"EXIT", (server_addr, server_port))
        running = False

    except Exception as e:
        print("Erro input_thread:", e)


def receive_thread(sock):
    global running

    while running:
        try:
            resposta, server = sock.recvfrom(1024)
            resposta = resposta.decode().strip()
            partes = resposta.split()

            ##########################################
            # NACK: servidor detectou perda
            ##########################################
            if len(partes) == 1:

                ultimo_confirmado = int(partes[0])
                faltante = ultimo_confirmado + 1

                # não reenvia aqui
                # só sinaliza para input_thread
                retransmit_queue.put(faltante)

                continue

            ##########################################
            # resposta normal
            ##########################################
            if len(partes) == 8:

                _, id_req, _, value, _, num_reqs, _, total_sum = partes
                req_id = int(id_req)

                with lock:
                    historico.pop(req_id, None)
                    if req_id in acks:
                        acks[req_id].set()

                imprimir_retorno(server[0], id_req, value, num_reqs, total_sum)
                continue

            print("Mensagem inesperada:", resposta)
            
        except socket.timeout:
            continue

        except Exception as e:
            print("Erro receive_thread:", e)
            break


def teste_arquivo(caminho_arquivo, client_socket, server_ip, server_port):
    global client_sock 
    global server_addr_global 
    global server_port_global 

    client_sock = client_socket
    server_addr_global = server_ip
    server_port_global = server_port

    t1 = threading.Thread(target=input_thread, args=(client_socket, server_ip, server_port,caminho_arquivo))
    t2 = threading.Thread(target=receive_thread, args=(client_socket,))

    t1.start()
    t2.start()

    t1.join()
    t2.join()
