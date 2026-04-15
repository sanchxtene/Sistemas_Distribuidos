import datetime

def imprimir_conexao(server_ip):
    time = datetime.datetime.now()
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"{time_str} "
          f"server_addr {server_ip} ")
    
def imprimir_retorno(server_ip, req_id, numero, num_reqs, total_sum):
    time = datetime.datetime.now()
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"{time_str} "
          f"server {server_ip} "
          f"id_req {req_id} "
          f"value {numero} "
          f"num_reqs {num_reqs} "
          f"total_sum {total_sum} ")