import json
import numpy as np

from cluster import enviar_members_update, replicar_estado
from print_servidor import imprimir_duplicada, imprimir_requisicao, retorno_requisicao


def discovery_loop(discovery_sock, porta, estado):
  while estado.role == "PRIMARY":

    try:
      data, addr = discovery_sock.recvfrom(1024)

      if data.decode() != "DISCOVERY":
        continue

      payload = {
        "ip": "127.0.0.1",
        "porta": porta,
        "rm_id": estado.rm_id
      }

      discovery_sock.sendto(json.dumps(payload).encode(), addr)

    except Exception:
        pass
    

def cluster_loop(cluster_sock, estado):
  while True:

    try:
      data, addr = cluster_sock.recvfrom(1024)

      msg = data.decode()

      # UPDATE BACKUPS 
      if msg.startswith("CLUSTER|"):

        payload = json.loads(msg[len("CLUSTER|"):])

        # NOVO SERVIDOR
        if payload["type"] == "MEMBERS_UPDATE":

          with estado.membership_lock:
            estado.members = {
              int(k): tuple(v)
              for k, v in payload["members"].items()
            }

          print("MEMBERS atualizado:")
          print(estado.members)

          continue

        # UPDATE SOMA TOTAL 
        elif payload["type"] == "STATE_UPDATE":

          with estado.state_lock:

              estado.req_global = payload["req_global"]
              estado.total = np.uint64(payload["total"])

              estado.tabela_servidor["num_reqs"] = estado.req_global
              estado.tabela_servidor["total_sum"] = estado.total

          print(
            f"[RM {estado.rm_id}] Estado atualizado: "
            f"reqs={estado.req_global} total={estado.total}"
          )

          continue
      
      # DISCOVERY SERVIDOR
      elif msg == "RM_DISCOVERY":
        if estado.role == "PRIMARY":
          print(f"RM_DISCOVERY recebido de {addr}")
          resposta = (f"PRIMARY_HERE|{estado.rm_id}")
          cluster_sock.sendto(resposta.encode(), addr)

      # JOIN NOVO SERVIDOR
      elif msg == "JOIN":
        with estado.membership_lock:
          novo_id = estado.next_id
          estado.members[novo_id] = addr
          estado.next_id += 1
          payload = {
              "type": "JOIN_ACK",
              "rm_id": novo_id,
              "primary_id": estado.primary_id,
              "members": dict(estado.members)
          }

          resposta = f"CLUSTER|{json.dumps(payload)}"

          cluster_sock.sendto(resposta.encode(), addr)

          enviar_members_update(cluster_sock, estado.members)

    except Exception as e:
                print("ERRO CLUSTER:", e)

def processamento_loop(service_sock, cluster_sock, estado):
  while True:
    # Mensagem recebida pelo servidor
    data, addr = service_sock.recvfrom(1024)

    msg = data.decode()

    try:
      with estado.state_lock:
        if addr not in estado.tabela_clientes:
          estado.tabela_clientes[addr] = {
              "last_req": 0,
              "last_num_reqs": 0,
              "last_total_sum": np.uint64(0)
          }

      # formato: req_id|numero
      id_req_user, numero = msg.split('|')
      id_req_user = int(id_req_user)
      numero = int(numero)

      # Consulta tabela para ver o id da última requisição do cliente
      id_ultima_requisicao = estado.tabela_clientes[addr]["last_req"]
      id_requisicao_esperada = id_ultima_requisicao + 1 

      # mensagem duplicada
      if id_req_user < id_requisicao_esperada:
        imprimir_duplicada(estado.tabela_clientes, addr, numero)
        continue
      # mensagem fora de ordem, se for maior que id esperado alguma mensagem se perdeu no caminho
      elif id_req_user > id_requisicao_esperada: 
        """
            Por outro lado, caso o servidor receba uma mensagem do cliente com um número de identificação superior ao
        próximo identificador esperado, o servidor deverá responder a requisição com uma mensagem de ACK com o
        último número de identificação de requisição recebida e processada, indicando assim que alguma requisição
        anterior foi perdida.
        """
        resposta = f"{id_ultima_requisicao}"
        service_sock.sendto(resposta.encode(), addr)
        continue

      # soma ao acumulador e incrementa contador de requisições
      with estado.state_lock:

        estado.total += np.uint64(numero)
        estado.req_global += 1

        req_global = estado.req_global
        total = estado.total

        estado.tabela_servidor["num_reqs"] = estado.req_global
        estado.tabela_servidor["total_sum"] = estado.total

        # Atualizar tabela clientes
        estado.tabela_clientes[addr]["last_req"] = id_req_user
        estado.tabela_clientes[addr]["last_num_reqs"] = estado.req_global
        estado.tabela_clientes[addr]["last_total_sum"] = estado.total

      replicar_estado(cluster_sock, estado.members, estado.rm_id, req_global, total)

      # Envia ACK ao cliente
      imprimir_requisicao(estado.tabela_clientes, addr, numero)
      resposta = retorno_requisicao(estado.tabela_clientes, addr, numero)

      service_sock.sendto(resposta.encode(), addr)

    except Exception as e:
      continue