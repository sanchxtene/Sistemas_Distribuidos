import sys
import socket
import numpy as np
import threading
import json
import time

from print_servidor import imprimir_inicializacao
from cluster import descobrir_lider, desserializar_clientes
from loops import cluster_loop, heartbeat_loop, monitor_loop, processamento_loop
from estado import ServidorState

# Porta de comunicacao recebida por parametro: python3 servidor.py 4000
if len(sys.argv) < 2:
    print("Erro - Falta de Parametros - Entrada deve ser: python servidor.py <PORTA>")
    sys.exit(1)

porta = int(sys.argv[1])
cluster_port = porta + 100

BROADCAST_IP = '255.255.255.255'

# Socket de servico (requisicoes e descoberta dos clientes).
service_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
service_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
service_sock.bind(('', porta))

# Socket de comunicacao entre servidores (cluster).
cluster_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cluster_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
cluster_sock.bind(('', cluster_port))

estado = ServidorState()

# Endereco de servico anunciado aos clientes (ip do host, porta de servico).
ip_host = socket.gethostbyname(socket.gethostname())
estado.service_addr = (ip_host, porta)
# Endereco deste RM no cluster (usado entre servidores).
estado.cluster_addr = (ip_host, cluster_port)

lider = descobrir_lider(cluster_sock, cluster_port)

if lider is None:
    # Nenhum primario ativo: este RM assume como PRIMARY (RM 1).
    estado.rm_id = 1
    estado.role = "PRIMARY"
    estado.next_id = 2
    estado.primary_id = estado.rm_id
    estado.primary_addr = estado.service_addr
    # members guarda o endereco de CLUSTER de cada RM.
    estado.members[estado.rm_id] = estado.cluster_addr
    estado.last_heartbeat = time.monotonic()

    print(f"RM {estado.rm_id} iniciado como PRIMARY")

else:
    # Existe um primario: entra como BACKUP e sincroniza o estado.
    cluster_sock.settimeout(2)
    cluster_sock.sendto(b"JOIN", lider)

    try:
        data, _ = cluster_sock.recvfrom(65535)
        msg = data.decode()

        if not msg.startswith("CLUSTER|"):
            raise Exception(f"Mensagem inesperada: {msg}")

        payload = json.loads(msg[len("CLUSTER|"):])

        estado.rm_id = payload["rm_id"]
        estado.primary_id = payload["primary_id"]
        estado.primary_addr = tuple(payload["primary_addr"])
        estado.members = {int(k): tuple(v) for k, v in payload["members"].items()}
        estado.next_id = payload["next_id"]

        estado.req_global = payload["req_global"]
        estado.total = np.uint64(payload["total"])
        estado.tabela_clientes = desserializar_clientes(payload["clientes"])

        estado.tabela_servidor["num_reqs"] = estado.req_global
        estado.tabela_servidor["total_sum"] = estado.total

        estado.role = "BACKUP"
        estado.last_heartbeat = time.monotonic()

        print(f"RM {estado.rm_id} iniciado como BACKUP (lider={estado.primary_id})")

    except socket.timeout:
        print("Falha ao entrar no cluster")
        sys.exit(1)
    finally:
        cluster_sock.settimeout(None)

# Primeira linha obrigatoria de saida do servidor.
imprimir_inicializacao(estado.tabela_servidor)

threading.Thread(target=cluster_loop, args=(cluster_sock, estado), daemon=True).start()
threading.Thread(target=heartbeat_loop, args=(cluster_sock, estado), daemon=True).start()
threading.Thread(target=monitor_loop, args=(cluster_sock, estado), daemon=True).start()

processamento_thread = threading.Thread(
    target=processamento_loop,
    args=(service_sock, cluster_sock, estado),
    daemon=True,
)
processamento_thread.start()

try:
    processamento_thread.join()
except KeyboardInterrupt:
    print("\nEncerrando servidor...")
    sys.exit(0)
