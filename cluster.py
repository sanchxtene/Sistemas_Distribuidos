import socket
import json
import numpy as np
from obter_ip_maquina import obter_ip_local

BROADCAST_IP = '255.255.255.255'

# Cria um json para passar a tabela de clientes por mensagem
def serializar_clientes(tabela_clientes):

    resultado = {}

    for (ip, porta), dados in tabela_clientes.items():

        resultado[f"{ip}:{porta}"] = {
            "last_req": dados["last_req"],
            "last_num_reqs": dados["last_num_reqs"],
            "last_total_sum": int(dados["last_total_sum"])
        }

    return resultado

# Desserializa a mensagem json com a tabela de clientes
def desserializar_clientes(clientes_json):

    resultado = {}

    for chave, dados in clientes_json.items():

        ip, porta = chave.split(":")

        resultado[(ip, int(porta))] = {
            "last_req": dados["last_req"],
            "last_num_reqs": dados["last_num_reqs"],
            "last_total_sum": np.uint64(dados["last_total_sum"])
        }

    return resultado


def descobrir_lider(sock, cluster_port):
    sock.settimeout(2)

    try:
        sock.sendto(b"RM_DISCOVERY", (BROADCAST_IP, cluster_port))

        while True:

            data, addr = sock.recvfrom(1024)
            msg = data.decode().strip()

            # ignora o próprio broadcast
            if addr[0] == obter_ip_local():
                continue

            if msg.startswith("PRIMARY_HERE"):
                print("Líder encontrado:", addr)
                return addr

    except socket.timeout:
        return None

    finally:
        sock.settimeout(None)


def enviar_members_update(sock, members, meu_id, next_id):

    payload = {
        "type": "MEMBERS_UPDATE",
        "members": members,
        "next_id": next_id
    }

    msg = f"CLUSTER|{json.dumps(payload)}"

    for rm_id, addr in members.items():

        if rm_id == meu_id:
            continue

        try:
            sock.sendto(msg.encode(), addr)

        except Exception:
            pass
        

def replicar_estado(sock, members, meu_id, req_global, total, tabela_clientes):

    payload = {
        "type": "STATE_UPDATE",
        "req_global": req_global,
        "total": int(total),
        "clientes": serializar_clientes(tabela_clientes),
    }

    msg = f"CLUSTER|{json.dumps(payload)}"

    for rm_id, addr in members.items():

        if rm_id == meu_id:
            continue

        try:
            sock.sendto(msg.encode(), addr)

        except Exception as e:
            print(f"Erro ao replicar para RM {rm_id}: {e}")


