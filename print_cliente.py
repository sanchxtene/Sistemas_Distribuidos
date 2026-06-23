import datetime


def _agora():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# Linha obrigatoria apos a descoberta do servidor:
# "AAAA-MM-DD HH:MM:SS server_addr <ip>"
def imprimir_conexao(server_ip):
    print(f"{_agora()} "
          f"server_addr {server_ip}")


# Linha obrigatoria apos receber a resposta do servidor:
# "AAAA-MM-DD HH:MM:SS server <ip> id_req <id> value <n> num_reqs <g> total_sum <s>"
def imprimir_retorno(server_ip, req_id, numero, num_reqs, total_sum):
    print(f"{_agora()} "
          f"server {server_ip} "
          f"id_req {req_id} "
          f"value {numero} "
          f"num_reqs {num_reqs} "
          f"total_sum {total_sum}")
