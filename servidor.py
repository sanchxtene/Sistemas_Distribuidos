import sys
import socket
import numpy as np
from print_servidor import imprimir_inicializacao, imprimir_duplicada, imprimir_requisicao, retorno_requisicao


# Configuração da porta servidor passada por parâmetro
if len(sys.argv) < 2:
    print("Erro - Falta de Parametros - Entrada deve ser: python cliente.py <PORTA>")
    exit()
porta = int(sys.argv[1])

# Cria o socket 
servidor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
servidor.bind(('', porta))
print(f"Servidor rodando na porta {porta}")

# Acumulador e contador de requisições totais
total = np.uint64(0)
req_global = 0

# Aramazena address (como indice), last_req, last_num_reqs, e last_total_sum
tabela_clientes = {}

tabela_servidor = {
    "num_reqs": 0,
    "total_sum": np.uint64(0)
}

imprimir_inicializacao(tabela_servidor)

while True:
    # Mensagem recebida pelo servidor
    data, addr = servidor.recvfrom(1024)
    msg = data.decode()
    
    # DISCOVERY
    if msg == "DISCOVERY":
        if addr not in tabela_clientes:
            # Cria cliente na tabela
            tabela_clientes[addr] = {
                "last_req": 0,
                "last_num_reqs": 0,
                "last_total_sum": np.uint64(0)
            }
            # Envia resposta ao cliente contendo o IP do servidor
            resposta = f"{socket.gethostbyname(socket.gethostname())}"
            servidor.sendto(resposta.encode(), addr)

    # PROCESSAMENTO
    else:
        try:
            # formato: req_id|numero
            id_req_user, numero = msg.split('|')
            id_req_user = int(id_req_user)
            numero = int(numero)

            # Consulta tabela para ver o id da última requisição do cliente
            id_ultima_requisicao = tabela_clientes[addr]["last_req"]
            id_requisicao_esperada = id_ultima_requisicao + 1 

            # mensagem duplicada
            if id_req_user < id_requisicao_esperada:
                imprimir_duplicada(tabela_clientes, addr, numero)
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
                servidor.sendto(resposta.encode(), addr)
                continue

            # soma ao acumulador e incrementa contador de requisições
            total += np.uint64(numero)
            req_global += 1

            # Atualizar tabela clientes
            tabela_clientes[addr]["last_req"] = id_req_user
            tabela_clientes[addr]["last_num_reqs"] = req_global
            tabela_clientes[addr]["last_total_sum"] = total

            # Atualizar tabela servidor
            tabela_servidor["num_reqs"] = req_global 
            tabela_servidor["total_sum"] = total

            # Envia ACK ao cliente
            imprimir_requisicao(tabela_clientes, addr, numero)
            resposta = retorno_requisicao(tabela_clientes, addr, numero)
            servidor.sendto(resposta.encode(), addr)

        except Exception as e:
            continue
