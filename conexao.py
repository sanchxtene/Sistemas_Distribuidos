import socket
import threading
import json
import time
import traceback

from print_cliente import imprimir_conexao, imprimir_retorno

BROADCAST_IP = '255.255.255.255'

# Timeout de retransmissao. A especificacao sugere ~3x RTT da rede local ou
# 10 ms. Em rede local 10 ms e adequado; aumente se houver muita perda.
RETRY_TIMEOUT = 0.010
DISCOVERY_TIMEOUT = 1.0
DISCOVERY_TENTATIVAS = 3
# Apos este numero de retransmissoes sem ACK, forca rediscovery do lider.
# 100 * 10ms = ~1s, suficiente para distinguir perda pontual de queda de lider.
RETRIES_BEFORE_REDISCOVER = 100
# Timeout de polling da thread de recepcao, para detectar rediscovery pendente.
RECV_POLL_TIMEOUT = 0.5

# Estado compartilhado entre as threads do cliente.
running = True
leader_lock = threading.Lock()
SERVER_IP = None
SERVER_PORT = None

# Sincronizacao envio <-> recepcao. Como o cliente mantem no maximo uma
# requisicao em voo, basta um unico evento e o id confirmado mais recente.
_ack_lock = threading.Lock()
_ack_event = threading.Event()
_ack_em_voo = None        # id_req aguardando confirmacao
_ultimo_confirmado = 0    # maior id confirmado pelo servidor

# Sinalizado pelo emissor quando suspeita que o lider caiu (varias
# retransmissoes sem ACK). A thread de recepcao trata, pois ela detem a
# leitura do socket.
_needs_rediscovery = threading.Event()


def _destino():
    with leader_lock:
        return (SERVER_IP, SERVER_PORT)


def conectar_com_servidor(client_socket, porta_descoberta):
    """Fase de descoberta: faz broadcast e aguarda o unicast do servidor.

    Retorna (ip, porta) do servidor ou None apos esgotar as tentativas.
    """
    global SERVER_IP, SERVER_PORT

    for tentativa in range(1, DISCOVERY_TENTATIVAS + 1):
        try:
            client_socket.settimeout(DISCOVERY_TIMEOUT)
            client_socket.sendto(b"DISCOVERY", (BROADCAST_IP, porta_descoberta))

            data, _ = client_socket.recvfrom(1024)
            payload = json.loads(data.decode())

            with leader_lock:
                SERVER_IP = payload["ip"]
                SERVER_PORT = payload["porta"]

            client_socket.settimeout(None)
            imprimir_conexao(SERVER_IP)
            return SERVER_IP, SERVER_PORT

        except socket.timeout:
            print(f"Timeout na descoberta ({tentativa}/{DISCOVERY_TENTATIVAS})")
        except Exception:
            traceback.print_exc()

    print(f"Servidor nao respondeu apos {DISCOVERY_TENTATIVAS} tentativas")
    client_socket.settimeout(None)
    return None


def reconectar(client_socket, porta_descoberta):
    """Redescobre o lider (ex.: apos failover). Bloqueia ate encontrar um."""
    global SERVER_IP, SERVER_PORT

    print("Procurando novo lider...")
    while running:
        if conectar_com_servidor(client_socket, porta_descoberta):
            print(f"Novo lider: {SERVER_IP}:{SERVER_PORT}")
            return SERVER_IP, SERVER_PORT
        time.sleep(0.5)
    return None


def enviar_com_timeout(sock, req_id, numero):
    """Envia uma requisicao e retransmite ate receber a confirmacao.

    Garante exactly-once: o id so e dado por concluido quando o servidor o
    confirma. Como ha no maximo uma requisicao em voo, o controle e simples.
    """
    global _ack_em_voo

    mensagem = f"{req_id}|{numero}".encode()

    with _ack_lock:
        _ack_em_voo = req_id
        _ack_event.clear()
        # Se o servidor ja confirmou este id (ACK anterior), nao reenvia.
        if _ultimo_confirmado >= req_id:
            _ack_em_voo = None
            return True

    retries = 0
    while running:
        try:
            sock.sendto(mensagem, _destino())
        except OSError:
            # Em Windows, sendto para um destino morto pode lancar
            # ConnectionResetError apos ICMP unreachable. Ignora e marca
            # rediscovery para nao matar a thread principal.
            _needs_rediscovery.set()

        # Acorda por confirmacao OU por sinal de lacuna; em ambos os casos
        # checamos se ESTE id ja foi confirmado. Lacuna -> reenvia.
        _ack_event.wait(timeout=RETRY_TIMEOUT)
        with _ack_lock:
            confirmado = _ultimo_confirmado >= req_id
            _ack_event.clear()
        if confirmado:
            with _ack_lock:
                _ack_em_voo = None
            return True

        # Apos varias retransmissoes sem ACK, o lider provavelmente caiu sem
        # gerar ICMP local (cenario comum quando o servidor estava em outra
        # maquina). Sinaliza para a thread de recepcao redescobrir o lider.
        retries += 1
        if retries >= RETRIES_BEFORE_REDISCOVER:
            retries = 0
            _needs_rediscovery.set()

    return False


def receive_thread(sock, client_socket, porta_descoberta):
    """Escuta as respostas do servidor e libera o envio da proxima requisicao.

    - ACK normal (8 tokens): confirma o id e imprime a resposta.
    - ACK de lacuna (1 token = ultimo id processado): acorda o emissor para
      retransmitir imediatamente, sem esperar o timeout.
    """
    global running, SERVER_IP, SERVER_PORT, _ultimo_confirmado

    while running:
        try:
            # Polling curto para conseguir tratar pedidos de rediscovery
            # vindos do emissor mesmo quando o lider parou de responder.
            sock.settimeout(RECV_POLL_TIMEOUT)
            data, server = sock.recvfrom(1024)
            partes = data.decode().split()

            # Resposta normal de processamento.
            if len(partes) == 8:
                req_id = int(partes[1])
                value = partes[3]
                num_reqs = partes[5]
                total_sum = partes[7]

                with _ack_lock:
                    if req_id > _ultimo_confirmado:
                        _ultimo_confirmado = req_id
                    if _ack_em_voo == req_id:
                        _ack_event.set()

                imprimir_retorno(server[0], req_id, value, num_reqs, total_sum)
                continue

            # ACK de lacuna: servidor informa o ultimo id que processou.
            if len(partes) == 1:
                ultimo = int(partes[0])
                with _ack_lock:
                    if ultimo > _ultimo_confirmado:
                        _ultimo_confirmado = ultimo
                    # Acorda o emissor para reenviar a requisicao em voo.
                    _ack_event.set()
                continue

        except socket.timeout:
            # Janela para tratar rediscovery sinalizado pelo emissor.
            if _needs_rediscovery.is_set():
                _needs_rediscovery.clear()
                novo = reconectar(client_socket, porta_descoberta)
                if novo:
                    with leader_lock:
                        SERVER_IP, SERVER_PORT = novo
                    # Acorda o emissor para reenviar imediatamente ao novo lider.
                    _ack_event.set()
            continue
        except ConnectionResetError:
            _needs_rediscovery.clear()
            novo = reconectar(client_socket, porta_descoberta)
            if novo:
                with leader_lock:
                    SERVER_IP, SERVER_PORT = novo
                _ack_event.set()
            continue
        except Exception:
            if running:
                traceback.print_exc()
            break
