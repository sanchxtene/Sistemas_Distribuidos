import datetime


def _agora():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# Primeira linha obrigatoria apos iniciar o servidor:
# "AAAA-MM-DD HH:MM:SS num_reqs 0 total_sum 0"
def imprimir_inicializacao(tabela):
    print(f"{_agora()} "
          f"num_reqs {tabela['num_reqs']} "
          f"total_sum {tabela['total_sum']}")


# Requisicao recebida em duplicidade: reexibe a ultima mensagem do cliente
# "AAAA-MM-DD HH:MM:SS client <ip> DUP!! id_req <id> value <n> num_reqs <g> total_sum <s>"
def imprimir_duplicada(addr, id_req, numero, num_reqs, total_sum):
    print(f"{_agora()} "
          f"client {addr[0]} "
          f"DUP!! "
          f"id_req {id_req} "
          f"value {numero} "
          f"num_reqs {num_reqs} "
          f"total_sum {total_sum}")


# Requisicao nova processada:
# "AAAA-MM-DD HH:MM:SS client <ip> id_req <id> value <n> num_reqs <g> total_sum <s>"
def imprimir_requisicao(addr, id_req, numero, num_reqs, total_sum):
    print(f"{_agora()} "
          f"client {addr[0]} "
          f"id_req {id_req} "
          f"value {numero} "
          f"num_reqs {num_reqs} "
          f"total_sum {total_sum}")


# Monta o ACK enviado ao cliente. Inclui o agregado global parcial.
# Formato: "id_req <id> value <n> num_reqs <g> total_sum <s>"
def retorno_requisicao(id_req, numero, num_reqs, total_sum):
    return (f"id_req {id_req} "
            f"value {numero} "
            f"num_reqs {num_reqs} "
            f"total_sum {total_sum}")
