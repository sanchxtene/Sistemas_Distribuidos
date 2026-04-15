import datetime

def imprimir_inicializacao(tabela):
    time = datetime.datetime.now()
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"{time_str} "
          f"num_reqs {tabela['num_reqs']} "
          f"total_sum {tabela['total_sum']} ")
         

def imprimir_duplicada(tabela, addr, numero):
    time = datetime.datetime.now()
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"{time_str} "
          f"client {str(addr[0])} "
          f"DUP!!"
          f"id_req {tabela[addr]['last_req']} "
          f"value {numero} "
          f"num_reqs {tabela[addr]['last_num_reqs']} "
          f"total_sum {tabela[addr]['last_total_sum']} ")
    

def imprimir_requisicao(tabela, addr, numero):
    time = datetime.datetime.now()
    time_str = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"{time_str} "
           f"client {str(addr[0])} "
           f"id_req {tabela[addr]['last_req']} "
           f"value {numero} "
           f"num_reqs {tabela[addr]['last_num_reqs']} "
           f"total_sum {tabela[addr]['last_total_sum']} ")


def retorno_requisicao(tabela, addr, numero):
    return(f"id_req {tabela[addr]['last_req']} "
           f"value {numero} "
           f"num_reqs {tabela[addr]['last_num_reqs']} "
           f"total_sum {tabela[addr]['last_total_sum']} ")