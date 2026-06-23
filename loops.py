import json
import socket
import threading
import time

import numpy as np

from cluster import (
    desserializar_clientes,
    enviar_members_update,
    replicar_delta,
    serializar_clientes,
)
from print_servidor import imprimir_duplicada, imprimir_requisicao, retorno_requisicao


HEARTBEAT_INTERVAL = 1.0
HEARTBEAT_TIMEOUT = 3.0
ELECTION_WAIT_TIMEOUT = 1.0
MONITOR_INTERVAL = 0.5


# ---------------------------------------------------------------------------
# Helpers de cluster
# ---------------------------------------------------------------------------

def _snapshot_members(estado):
    with estado.membership_lock:
        return dict(estado.members)


def _cluster_message(payload):
    return f"CLUSTER|{json.dumps(payload)}"


def _send_to_members(sock, members, meu_id, payload):
    """Envia uma mensagem de cluster a todos os membros (menos a si mesmo)."""
    msg = _cluster_message(payload).encode()

    for rm_id, addr in members.items():
        if rm_id == meu_id:
            continue
        try:
            sock.sendto(msg, addr)
        except Exception:
            pass


def _anunciar_lider(cluster_sock, estado):
    payload = {
        "type": "COORDINATOR",
        "leader_id": estado.rm_id,
        # primary_addr e sempre o endereco de SERVICO (porta de clientes)
        "leader_addr": list(estado.primary_addr or estado.service_addr),
    }
    _send_to_members(cluster_sock, _snapshot_members(estado), estado.rm_id, payload)


def _atualizar_lider(estado, leader_id, leader_addr):
    with estado.state_lock:
        estado.primary_id = leader_id
        estado.primary_addr = tuple(leader_addr)
        estado.last_heartbeat = time.monotonic()
        if estado.rm_id != leader_id:
            estado.role = "BACKUP"


# ---------------------------------------------------------------------------
# Eleicao (algoritmo Bully)
# ---------------------------------------------------------------------------

def _iniciar_eleicao(cluster_sock, estado):
    with estado.membership_lock:
        if estado.election_in_progress:
            return
        estado.election_in_progress = True

    try:
        estado.election_ok_event.clear()

        higher_members = {
            rm_id: addr
            for rm_id, addr in _snapshot_members(estado).items()
            if rm_id > estado.rm_id
        }

        if higher_members:
            _send_to_members(
                cluster_sock,
                higher_members,
                estado.rm_id,
                {"type": "ELECTION", "candidate_id": estado.rm_id},
            )

            # Se algum RM com id maior responde OK, ele assume a eleicao.
            if estado.election_ok_event.wait(timeout=ELECTION_WAIT_TIMEOUT):
                return

        # Ninguem maior respondeu: este RM vira o lider.
        with estado.state_lock:
            estado.role = "PRIMARY"
            estado.primary_id = estado.rm_id
            estado.primary_addr = estado.service_addr
            estado.last_heartbeat = time.monotonic()

        _anunciar_lider(cluster_sock, estado)
        print(f"RM {estado.rm_id} assumiu como PRIMARY")

    finally:
        with estado.membership_lock:
            estado.election_in_progress = False


# ---------------------------------------------------------------------------
# Threads de cluster
# ---------------------------------------------------------------------------

def heartbeat_loop(cluster_sock, estado):
    """Lider envia heartbeats periodicos aos backups."""
    while True:
        time.sleep(HEARTBEAT_INTERVAL)

        if estado.role != "PRIMARY":
            continue

        _send_to_members(
            cluster_sock,
            _snapshot_members(estado),
            estado.rm_id,
            {
                "type": "HEARTBEAT",
                "leader_id": estado.rm_id,
                "leader_addr": list(estado.primary_addr or estado.service_addr),
            },
        )


def monitor_loop(cluster_sock, estado):
    """Backup detecta a falha do lider e dispara eleicao.

    Roda em thread separada para nao depender de timeout no recvfrom do
    cluster_loop (que fica bloqueado a maior parte do tempo).
    """
    while True:
        time.sleep(MONITOR_INTERVAL)

        if estado.role != "BACKUP":
            continue

        if time.monotonic() - estado.last_heartbeat > HEARTBEAT_TIMEOUT:
            _iniciar_eleicao(cluster_sock, estado)


def cluster_loop(cluster_sock, estado):
    """Trata todo o trafego RM<->RM: membership, replicacao e eleicao."""
    while True:
        try:
            data, addr = cluster_sock.recvfrom(65535)
            msg = data.decode()

            if msg.startswith("CLUSTER|"):
                payload = json.loads(msg[len("CLUSTER|"):])
                tipo = payload["type"]

                if tipo == "MEMBERS_UPDATE":
                    with estado.membership_lock:
                        estado.members = {
                            int(k): tuple(v)
                            for k, v in payload["members"].items()
                        }
                        estado.next_id = payload["next_id"]
                    continue

                if tipo == "STATE_FULL":
                    # Snapshot completo (usado em sincronizacao inicial).
                    with estado.state_lock:
                        estado.req_global = payload["req_global"]
                        estado.total = np.uint64(payload["total"])
                        estado.tabela_clientes = desserializar_clientes(payload["clientes"])
                        estado.tabela_servidor["num_reqs"] = estado.req_global
                        estado.tabela_servidor["total_sum"] = estado.total
                    continue

                if tipo == "STATE_DELTA":
                    # Replicacao incremental: aplica uma requisicao processada
                    # pelo primario. Idempotente por (cliente, id_req).
                    cli = tuple(payload["client"])
                    id_req = payload["id_req"]
                    numero = np.uint64(payload["value"])

                    with estado.state_lock:
                        dados = estado.tabela_clientes.get(cli)
                        if dados is None:
                            dados = {
                                "last_req": 0,
                                "last_num_reqs": 0,
                                "last_total_sum": np.uint64(0),
                            }
                            estado.tabela_clientes[cli] = dados

                        # Aplica somente se for a proxima requisicao esperada.
                        if id_req == dados["last_req"] + 1:
                            estado.total += numero
                            estado.req_global += 1
                            dados["last_req"] = id_req
                            dados["last_num_reqs"] += 1
                            dados["last_total_sum"] = estado.total
                            estado.tabela_servidor["num_reqs"] = estado.req_global
                            estado.tabela_servidor["total_sum"] = estado.total
                    continue

                if tipo == "HEARTBEAT":
                    _atualizar_lider(estado, payload["leader_id"], payload["leader_addr"])
                    continue

                if tipo == "OK":
                    estado.election_ok_event.set()
                    continue

                if tipo == "COORDINATOR":
                    _atualizar_lider(estado, payload["leader_id"], payload["leader_addr"])
                    estado.election_ok_event.clear()
                    with estado.membership_lock:
                        estado.election_in_progress = False
                    print(f"[RM {estado.rm_id}] Novo lider eleito: RM {estado.primary_id}")
                    continue

                if tipo == "ELECTION":
                    candidato_id = payload["candidate_id"]
                    if estado.rm_id > candidato_id:
                        cluster_sock.sendto(
                            _cluster_message({"type": "OK", "from_id": estado.rm_id}).encode(),
                            addr,
                        )
                        if estado.role == "PRIMARY":
                            _anunciar_lider(cluster_sock, estado)
                        else:
                            threading.Thread(
                                target=_iniciar_eleicao,
                                args=(cluster_sock, estado),
                                daemon=True,
                            ).start()
                    continue

            elif msg == "RM_DISCOVERY":
                if estado.role == "PRIMARY":
                    resposta = f"PRIMARY_HERE|{estado.rm_id}"
                    cluster_sock.sendto(resposta.encode(), addr)

            elif msg == "JOIN":
                if estado.role != "PRIMARY":
                    continue
                with estado.membership_lock:
                    novo_id = estado.next_id
                    # addr e o endereco de cluster do novo RM (ja correto).
                    estado.members[novo_id] = addr
                    estado.next_id += 1
                    membros_snapshot = dict(estado.members)
                    next_id_atual = estado.next_id

                with estado.state_lock:
                    payload = {
                        "type": "JOIN_ACK",
                        "rm_id": novo_id,
                        "primary_id": estado.primary_id,
                        "primary_addr": list(estado.primary_addr),
                        "members": membros_snapshot,
                        "next_id": next_id_atual,
                        "req_global": estado.req_global,
                        "total": int(estado.total),
                        "clientes": serializar_clientes(estado.tabela_clientes),
                    }

                cluster_sock.sendto(_cluster_message(payload).encode(), addr)
                enviar_members_update(cluster_sock, membros_snapshot, estado.rm_id, next_id_atual)

        except Exception as e:
            print("ERRO CLUSTER:", e)


# ---------------------------------------------------------------------------
# Processamento de requisicoes dos clientes
# ---------------------------------------------------------------------------

def processamento_loop(service_sock, cluster_sock, estado):
    """Recebe requisicoes dos clientes, soma ao acumulador e responde com ACK.

    Caminho quente: mantido enxuto para suportar grande volume de requisicoes.
    """
    while True:
        data, addr = service_sock.recvfrom(2048)

        # Somente o primario processa requisicoes de clientes.
        if estado.role != "PRIMARY":
            continue

        try:
            msg = data.decode()
        except Exception:
            continue

        # --- Descoberta (unicast de resposta ao broadcast do cliente) ---
        if msg == "DISCOVERY":
            payload = {
                "ip": estado.service_addr[0],
                "porta": estado.service_addr[1],
                "rm_id": estado.rm_id,
            }
            service_sock.sendto(json.dumps(payload).encode(), addr)
            continue

        if msg == "EXIT":
            continue

        sep = msg.find('|')
        if sep == -1:
            continue

        try:
            id_req_user = int(msg[:sep])
            numero = int(msg[sep + 1:])
        except ValueError:
            continue

        with estado.state_lock:
            dados = estado.tabela_clientes.get(addr)
            if dados is None:
                dados = {
                    "last_req": 0,
                    "last_num_reqs": 0,
                    "last_total_sum": np.uint64(0),
                }
                estado.tabela_clientes[addr] = dados

            esperada = dados["last_req"] + 1

            if id_req_user < esperada:
                # Duplicata: reexibe e reenvia o ACK da ultima requisicao
                # processada deste cliente (last_*).
                num_reqs_cli = dados["last_num_reqs"]
                total_cli = dados["last_total_sum"]
                last_req = dados["last_req"]
                global_reqs = estado.req_global
                global_total = estado.total
                acao = "DUP"

            elif id_req_user > esperada:
                # Lacuna: alguma requisicao anterior se perdeu. Responde com o
                # ultimo id processado para o cliente retransmitir.
                acao = "GAP"
                last_proc = dados["last_req"]

            else:
                # Proxima requisicao esperada: processa.
                estado.total += np.uint64(numero)
                estado.req_global += 1

                dados["last_req"] = id_req_user
                dados["last_num_reqs"] += 1
                dados["last_total_sum"] = estado.total

                estado.tabela_servidor["num_reqs"] = estado.req_global
                estado.tabela_servidor["total_sum"] = estado.total

                global_reqs = estado.req_global
                global_total = estado.total
                acao = "OK"

        # --- Fora do lock: I/O de rede e impressao ---

        if acao == "DUP":
            imprimir_duplicada(addr, last_req, numero, global_reqs, global_total)
            resposta = retorno_requisicao(last_req, numero, num_reqs_cli, total_cli)
            service_sock.sendto(resposta.encode(), addr)
            continue

        if acao == "GAP":
            service_sock.sendto(str(last_proc).encode(), addr)
            continue

        # acao == "OK"
        # Replicacao incremental best-effort aos backups. Em servidor unico
        # (members so contem a si proprio) nao ha custo de rede.
        membros = _snapshot_members(estado)
        if len(membros) > 1:
            replicar_delta(cluster_sock, membros, estado.rm_id, addr, id_req_user, numero)

        imprimir_requisicao(addr, id_req_user, numero, global_reqs, global_total)
        resposta = retorno_requisicao(id_req_user, numero, global_reqs, global_total)
        service_sock.sendto(resposta.encode(), addr)
