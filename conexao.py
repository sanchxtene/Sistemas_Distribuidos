import socket
import signal
import sys
import queue
import threading
from print_cliente import imprimir_conexao, imprimir_retorno

max_tentativas = 3

running = True
client_sock = None
server_addr_global = None
server_port_global = None

acks  = {}
historico = {}
lock = threading.Lock()

# fila de pedidos de retransmissão
retransmit_queue = queue.Queue()


def conectar_com_servidor(client_socket):
    tentativa = 0

    while tentativa < max_tentativas:
        try:
            # Servidor responde com o endereço IP
            data, server_addr = client_socket.recvfrom(1024)
            client_socket.settimeout(0.01)
            msg = data.decode()
            imprimir_conexao(msg)
            return server_addr[0]  # sucesso → sai do loop

        except socket.timeout:
            # Servidor não respondeu
            tentativa += 1
            print(f"Timeout... tentando conexão novamente ({tentativa}/{max_tentativas})")

    # TODAS as tentativas falharam
    print(f"Servidor não respondeu após {max_tentativas} tentativas")
    return None 


def encerrar_conexao(sig, frame):
    global running
    print("\nEncerrando cliente...")
    running = False
    try:
        if client_sock:
            client_sock.sendto(b"EXIT", (server_addr_global, server_port_global))
    except:
        pass


signal.signal(signal.SIGINT, encerrar_conexao)


def processar_retransmissoes(sock, server_addr, server_port):
    """
    Executado pelo input_thread.
    Processa pedidos de reenvio vindos da função receive_thread.
    """
    while not retransmit_queue.empty():

        faltante = retransmit_queue.get()

        with lock:
            msg = historico.get(faltante)

        if msg:
            sock.sendto(msg.encode(), (server_addr, server_port))


def enviar_com_timeout(sock, server_addr, server_port, req_id, numero):
    """
    Executado pelo manual_input_thread ou automatic_input_thread.
    Processa pedidos de envio utilizando timeout e várias tentativas caso necessário.
    """
    mensagem = f"{req_id}|{numero}"

    evento = threading.Event()

    with lock:
        acks[req_id] = evento
        historico[req_id] = mensagem

    for tentativa in range(max_tentativas):
        sock.sendto(
            mensagem.encode(),
            (server_addr, server_port)
        )

        if evento.wait(timeout=0.01):
            with lock:
                acks.pop(req_id,None)
            return True

    print("Servidor indisponível.")
    return False


def manual_input_thread(sock, server_addr, server_port):
    """
    Executada por cliente.py
    Recebe entradas do usuário pelo teclado e utiliza a função enviar_com_timeout para envia-las ao servidor.
    """
    global running
    global client_sock 
    global server_addr_global 
    global server_port_global 

    client_sock = sock
    server_addr_global = server_addr
    server_port_global = server_port

    req_id = 0

    try:
        while running:
            # antes de nova requisição,
            # verifica se servidor pediu reenvio
            processar_retransmissoes(sock, server_addr, server_port)

            entrada = input()

            numero = int(entrada)
            req_id += 1

            ok = enviar_com_timeout(sock, server_addr, server_port, req_id, numero)

            if not ok:
                running = False
                break

    except EOFError:
        print("\nEOF recebido. Encerrando...")
        sock.sendto(b"EXIT", (server_addr, server_port))
        running = False
    
    except KeyboardInterrupt:
        print("\nCTRL+C recebido. Encerrando...")
        sock.sendto(b"EXIT", (server_addr, server_port))
        running = False

    except Exception as e:
        print("Erro input_thread:", e)



def automatic_input_thread(sock, server_addr, server_port, caminho_arquivo):
    """
    Executada por cliente.py
    Recebe entradas vinda de um arquivo e utiliza a função enviar_com_timeout para envia-las ao servidor.
    """
    global running
    global client_sock 
    global server_addr_global 
    global server_port_global 

    client_sock = sock
    server_addr_global = server_addr
    server_port_global = server_port
    
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
    """
    Executada por cliente.py
    Responsável por ficar "escutando" o retorno do servidor
    Caso o servidor detecte a perda de uma mensagem deve adicionar
    o id da mensagem faltante para ser enviada novamente
    """
    global running

    while running:
        try:
            resposta, server = sock.recvfrom(1024)
            resposta = resposta.decode().strip()
            partes = resposta.split()

            ##########################################
            # servidor detectou perda
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