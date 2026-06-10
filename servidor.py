import sys
import socket
import numpy as np
import threading
import json
from print_servidor import imprimir_inicializacao
from cluster import descobrir_lider
from loops import discovery_loop, cluster_loop, processamento_loop
from estado import ServidorState

# Configuração da porta servidor passada por parâmetro
if len(sys.argv) < 2:
    print("Erro - Falta de Parametros - Entrada deve ser: python cliente.py <PORTA>")
    exit()
porta = int(sys.argv[1])

# Cria o sockets 
DISCOVERY_PORT = 3999

# clientes
service_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
service_sock.bind(('', porta))

# comunicação entre servidores
cluster_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cluster_sock.bind(('', porta + 100))

discovery_sock = None

print(f"Servidor rodando na porta {porta}")
print(f"Cluster na porta {porta+100}")

estado = ServidorState()

lider = descobrir_lider(cluster_sock, porta + 100)


if lider is None:

    estado.rm_id = 1
    estado.role = "PRIMARY"

    estado.next_id = 2

    estado.primary_id = estado.rm_id
    estado.primary_addr = ("localhost", porta)

    estado.members[estado.rm_id] = estado.primary_addr

    discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discovery_sock.bind(("", DISCOVERY_PORT))

    threading.Thread(
        target=discovery_loop,
        args=(
            discovery_sock,
            porta,
            estado
        ),
        daemon=True
    ).start()

    print(f"RM {estado.rm_id} iniciado como PRIMARY")

else:
    cluster_sock.settimeout(2)

    # Mensagem de JOIN ao Líder
    resposta = f"JOIN"
    cluster_sock.sendto(resposta.encode(), lider)

    try:
        data, server_addr = cluster_sock.recvfrom(1024)
        msg = data.decode()

        if not msg.startswith("CLUSTER|"):
            raise Exception(
                f"Mensagem inesperada: {msg}"
            )

        payload = json.loads(
            msg[len("CLUSTER|"):]
        )

        estado.rm_id = payload["rm_id"]
        estado.primary_id = payload["primary_id"]

        estado.members = {
            int(k): tuple(v)
            for k, v in payload["members"].items()
        }

        estado.role = "BACKUP"

        estado.primary_addr = lider

        print(
            f"RM {estado.rm_id} iniciado como BACKUP "
            f"(lider={estado.primary_id})"
        )

        print("MEMBERS:")
        print(estado.members)

    except socket.timeout:
        print("Falha ao entrar no cluster")
        exit()
    
    finally:
        cluster_sock.settimeout(None)

imprimir_inicializacao(estado.tabela_servidor)

cluster_thread = threading.Thread(
    target=cluster_loop,
    args=(
        cluster_sock,
        estado
    ),
    daemon=True
)

processamento_thread = threading.Thread(
    target=processamento_loop,
    args=(
        service_sock,
        cluster_sock,
        estado
    ),
    daemon=True
)

cluster_thread.start()
processamento_thread.start()

cluster_thread.join()
processamento_thread.join()

while True:
    threading.Event().wait(1)

