import socket
import json
import numpy as np

BROADCAST_IP = '255.255.255.255'

# Faixa de portas de cluster a varrer na descoberta do lider.
# O cluster escuta sempre em (porta_de_servico + 100).
CLUSTER_MIN_SCAN = 5
CLUSTER_MAX_SCAN = 20


def addr_cluster(addr_servico, cluster_port):
    """Converte um endereco de servico (ip, porta) no endereco de cluster.

    Mantido por compatibilidade; o cluster usa diretamente o endereco de
    origem dos datagramas, ja na porta correta.
    """
    ip, _ = addr_servico
    return (ip, cluster_port)


# Serializa a tabela de clientes para transporte em JSON.
def serializar_clientes(tabela_clientes):
    resultado = {}
    for (ip, porta), dados in tabela_clientes.items():
        resultado[f"{ip}:{porta}"] = {
            "last_req": dados["last_req"],
            "last_num_reqs": dados["last_num_reqs"],
            "last_total_sum": int(dados["last_total_sum"]),
        }
    return resultado


# Reconstroi a tabela de clientes a partir do JSON.
def desserializar_clientes(clientes_json):
    resultado = {}
    for chave, dados in clientes_json.items():
        ip, porta = chave.rsplit(":", 1)
        resultado[(ip, int(porta))] = {
            "last_req": dados["last_req"],
            "last_num_reqs": dados["last_num_reqs"],
            "last_total_sum": np.uint64(dados["last_total_sum"]),
        }
    return resultado


def descobrir_lider(sock, cluster_port):
    """Procura um PRIMARY ativo via broadcast de RM_DISCOVERY.

    Retorna o endereco de cluster do lider ou None se nenhum respondeu.
    """
    try:
        sock.settimeout(0.3)

        inicio = max(1, cluster_port - CLUSTER_MIN_SCAN)
        fim = cluster_port + CLUSTER_MAX_SCAN

        for porta in range(inicio, fim + 1):
            try:
                sock.sendto(b"RM_DISCOVERY", (BROADCAST_IP, porta))
            except Exception:
                pass

        # Janela curta para receber a primeira resposta de um PRIMARY.
        for _ in range(10):
            try:
                data, addr = sock.recvfrom(1024)
            except socket.timeout:
                break

            if data.decode().startswith("PRIMARY_HERE"):
                return addr

    except socket.timeout:
        pass
    finally:
        sock.settimeout(None)

    return None


def enviar_members_update(sock, members, meu_id, next_id):
    """Propaga a lista de membros atualizada a todos os backups."""
    payload = {
        "type": "MEMBERS_UPDATE",
        "members": members,
        "next_id": next_id,
    }
    msg = f"CLUSTER|{json.dumps(payload)}".encode()

    for rm_id, addr in members.items():
        if rm_id == meu_id:
            continue
        try:
            sock.sendto(msg, addr)
        except Exception:
            pass


def replicar_delta(sock, members, meu_id, cliente_addr, id_req, numero):
    """Replicacao incremental: envia apenas a requisicao recem-processada.

    Best-effort por UDP. Como o delta e idempotente por (cliente, id_req) e
    so aplicado se for o proximo esperado, perdas pontuais sao toleradas: a
    sincronizacao completa ocorre no JOIN e via STATE_FULL.
    """
    payload = {
        "type": "STATE_DELTA",
        "client": list(cliente_addr),
        "id_req": id_req,
        "value": int(numero),
    }
    msg = f"CLUSTER|{json.dumps(payload)}".encode()

    for rm_id, addr in members.items():
        if rm_id == meu_id:
            continue
        try:
            sock.sendto(msg, addr)
        except Exception:
            pass


def replicar_estado_completo(sock, members, meu_id, req_global, total, tabela_clientes):
    """Envia um snapshot completo do estado (sincronizacao/recuperacao)."""
    payload = {
        "type": "STATE_FULL",
        "req_global": req_global,
        "total": int(total),
        "clientes": serializar_clientes(tabela_clientes),
    }
    msg = f"CLUSTER|{json.dumps(payload)}".encode()

    for rm_id, addr in members.items():
        if rm_id == meu_id:
            continue
        try:
            sock.sendto(msg, addr)
        except Exception:
            pass
