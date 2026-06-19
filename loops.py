import json
import numpy as np
from cluster import enviar_members_update, replicar_estado, desserializar_clientes, serializar_clientes
from print_servidor import imprimir_duplicada, imprimir_requisicao, retorno_requisicao
from obter_ip_maquina import obter_ip_local
   
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
            estado.next_id = payload["next_id"]
          continue

        # UPDATE BACKUPS
        elif payload["type"] == "STATE_UPDATE":

          with estado.state_lock:

              estado.req_global = payload["req_global"]
              estado.total = np.uint64(payload["total"])

              estado.tabela_clientes = (
                  desserializar_clientes(payload["clientes"])
              )

              estado.tabela_servidor["num_reqs"] = estado.req_global
              estado.tabela_servidor["total_sum"] = estado.total

          print("\n=== ESTADO BACKUP ===")
          print("req_global =", estado.req_global)
          print("total =", estado.total)
          for addr, dados in estado.tabela_clientes.items():
              print(
                  f"cliente={addr[0]}:{addr[1]} | "
                  f"last_req={dados['last_req']} | "
                  f"num_reqs={dados['last_num_reqs']} | "
                  f"total_sum={dados['last_total_sum']}"
              )
          print("=====================\n")

          continue
      
      # DISCOVERY SERVIDOR
      elif msg == "RM_DISCOVERY":
        if estado.role == "PRIMARY":
          resposta = (f"PRIMARY_HERE|{estado.rm_id}")
          cluster_sock.sendto(resposta.encode(), addr)

      # JOIN NOVO SERVIDOR
      elif msg == "JOIN":
        with estado.membership_lock:
          novo_id = estado.next_id
          estado.members[novo_id] = addr
          estado.next_id += 1

          with estado.state_lock:
            payload = {
                "type": "JOIN_ACK",
                "rm_id": novo_id,
                "primary_id": estado.primary_id,
                "members": dict(estado.members),
                "next_id": estado.next_id,

                # estado atual do sistema
                "req_global": estado.req_global,
                "total": int(estado.total),
                "clientes": serializar_clientes(
                    estado.tabela_clientes
                )
            }

          resposta = f"CLUSTER|{json.dumps(payload)}"
          cluster_sock.sendto(resposta.encode(), addr)
          enviar_members_update(cluster_sock, estado.members, estado.rm_id, estado.next_id)

    except Exception as e:
                print("ERRO CLUSTER:", e)


def processamento_loop(service_sock, cluster_sock, estado):
  while True:
    # Mensagem recebida pelo servidor
    data, addr = service_sock.recvfrom(1024)

    msg = data.decode()

    if estado.role != "PRIMARY":
      continue

    if msg == "DISCOVERY":
  
      payload = {
          "ip":  obter_ip_local(),
          "porta": service_sock.getsockname()[1],
          "rm_id": estado.rm_id
      }

      service_sock.sendto(json.dumps(payload).encode(), addr)

      continue

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

      with estado.membership_lock:
        members = dict(estado.members)

      replicar_estado(cluster_sock, members, estado.rm_id, req_global, total, estado.tabela_clientes)

      # Envia ACK ao cliente
      imprimir_requisicao(estado.tabela_clientes, addr, numero)
      resposta = retorno_requisicao(estado.tabela_clientes, addr, numero)

      service_sock.sendto(resposta.encode(), addr)

      print("\n=== CLIENTES PRIMARY ===")
      for addr, dados in estado.tabela_clientes.items():
          print(addr, dados)
      print("========================\n")

    except Exception as e:
      print("ERRO PROCESSAMENTO:", e)
