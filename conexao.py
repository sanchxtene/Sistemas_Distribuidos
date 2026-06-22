import socket
import signal
import sys
import queue
import threading
import json
import time
import traceback
from print_cliente import imprimir_retorno

BROADCAST_IP = '255.255.255.255'

max_tentativas = 3

running = True
client_sock = None
SERVER_IP_global = None
SERVER_PORT_global = None

acks  = {}
historico = {}
lock = threading.Lock()

# fila de pedidos de retransmissão
retransmit_queue = queue.Queue()

leader_lock = threading.Lock()


def conectar_com_servidor(client_socket):
    tentativa = 0

    global SERVER_IP
    global SERVER_PORT

    while tentativa < max_tentativas:
        try:
            client_socket.settimeout(1)
            # Servidor responde com o endereço IP
            data, addr = client_socket.recvfrom(1024)

            payload = json.loads(data.decode())

            with leader_lock:
                SERVER_IP = payload["ip"]
                SERVER_PORT = payload["porta"]

            print(
                f"Conectado ao líder "
                f"{SERVER_IP}:{SERVER_PORT}"
            )

            client_socket.settimeout(None)

            return SERVER_IP, SERVER_PORT

        except socket.timeout:
            # Servidor não respondeu
            tentativa += 1
            print(f"Timeout... tentando conexão novamente ({tentativa}/{max_tentativas})")

    # TODAS as tentativas falharam
    print(f"Servidor não respondeu após {max_tentativas} tentativas")
    return None 


def reconectar(client_socket):
    global SERVER_IP
    global SERVER_PORT

    print("Tentando localizar novo líder...")

    while True:

        try:
            client_socket.sendto(b"DISCOVERY", (BROADCAST_IP, SERVER_PORT))

            resultado = conectar_com_servidor(client_socket)

            if resultado is None:
                raise RuntimeError("Nenhum líder encontrado")

            SERVER_IP, SERVER_PORT = resultado

            print(
                f"Novo líder encontrado: "
                f"{SERVER_IP}:{SERVER_PORT}"
            )

            return SERVER_IP, SERVER_PORT

        except Exception:

            print(
                "Nenhum líder disponível. "
                "Tentando novamente..."
            )

            time.sleep(1)


def encerrar_conexao(sig, frame):
    global SERVER_IP
    global SERVER_PORT
    global running

    print("\nEncerrando cliente...")
    
    running = False
    
    try:
        if client_sock:
            client_sock.sendto(b"EXIT", (SERVER_IP, SERVER_PORT))
    except:
        pass

    signal.signal(signal.SIGINT, encerrar_conexao)




def processar_retransmissoes(sock, SERVER_IP, SERVER_PORT):
    """
    Executado pelo input_thread.
    Processa pedidos de reenvio vindos da função receive_thread.
    """
    while not retransmit_queue.empty():

        faltante = retransmit_queue.get()

        with lock:
            msg = historico.get(faltante)

        if msg:
            sock.sendto(msg.encode(), (SERVER_IP, SERVER_PORT))


def enviar_com_timeout(sock, req_id, numero):
    """
    Executado pelo manual_input_thread ou automatic_input_thread.
    Processa pedidos de envio utilizando timeout e várias tentativas caso necessário.
    """
    global SERVER_IP
    global SERVER_PORT

    mensagem = f"{req_id}|{numero}"

    evento = threading.Event()

    with lock:
        acks[req_id] = evento
        historico[req_id] = mensagem

    for tentativa in range(max_tentativas):
        with leader_lock:
            destino = (SERVER_IP, SERVER_PORT)

        sock.sendto(mensagem.encode(), destino)

        if evento.wait(timeout=1):
            with lock:
                acks.pop(req_id,None)
            return True

    reconectar(sock)
    return False


def manual_input_thread(sock):
    """
    Executada por cliente.py
    Recebe entradas do usuário pelo teclado e utiliza a função enviar_com_timeout para envia-las ao servidor.
    """
    global running
    global client_sock 
    global SERVER_IP
    global SERVER_PORT

    req_id = 0

    try:
        while running:
            # antes de nova requisição,
            # verifica se servidor pediu reenvio
            processar_retransmissoes(sock, SERVER_IP, SERVER_PORT)

            entrada = input()

            numero = int(entrada)
            req_id += 1

            ok = enviar_com_timeout(sock, req_id, numero)

            if not ok:
                running = False
                break

    except EOFError:
        print("\nEOF recebido. Encerrando...")
        sock.sendto(b"EXIT", (SERVER_IP, SERVER_PORT))
        running = False
    
    except KeyboardInterrupt:
        print("\nCTRL+C recebido. Encerrando...")
        sock.sendto(b"EXIT", (SERVER_IP, SERVER_PORT))
        running = False

    except Exception as e:
        traceback.print_exc()


def automatic_input_thread(sock, caminho_arquivo):
    """
    Executada por cliente.py
    Recebe entradas vinda de um arquivo e utiliza a função enviar_com_timeout para envia-las ao servidor.
    """
    global running
    global client_sock 
    global SERVER_IP
    global SERVER_PORT
    
    req_id = 0

    try:
        with open(caminho_arquivo) as f:
            for linha in f:
                if not running:
                    break

                # antes de nova requisição,
                # verifica se servidor pediu reenvio
                processar_retransmissoes(sock, SERVER_IP, SERVER_PORT)

                linha = linha.strip()

                if not linha:
                    continue

                numero = int(linha)
                req_id += 1

                ok = enviar_com_timeout(sock, req_id, numero)

                if not ok:
                    running = False
                    break

            print("\nEOF recebido. Encerrando...")
            #sock.sendto(b"EXIT", (SERVER_IP, SERVER_PORT))
            #running = False
    
    except EOFError:
        print("\nEOF recebido. Encerrando...")
        #sock.sendto(b"EXIT", (SERVER_IP, SERVER_PORT))
        #running = False

    except Exception as e:
        traceback.print_exc()



def receive_thread(sock):
    """
    Executada por cliente.py
    Responsável por ficar "escutando" o retorno do servidor
    Caso o servidor detecte a perda de uma mensagem deve adicionar
    o id da mensagem faltante para ser enviada novamente
    """
    global running
    global SERVER_IP
    global SERVER_PORT

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
            
        except ConnectionResetError:
            print(
                "Servidor indisponível. "
                "Procurando novo líder..."
            )

            novo_ip, nova_porta = reconectar(sock)

            with leader_lock:
                SERVER_IP = novo_ip
                SERVER_PORT = nova_porta

            continue

        except Exception as e:
            traceback.print_exc()
            break