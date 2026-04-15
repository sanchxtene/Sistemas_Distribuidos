import sys
import socket
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

# Acumulador e requisições totais
total = 0
req_global = 0

# Aramazena address, last_req, last_num_reqs, e last_total_sum
tabela_clientes = {}

tabela_servidor = {
    "num_reqs": 0,
    "total_sum": 0
}

imprimir_inicializacao(tabela_servidor)

while True:
    data, addr = servidor.recvfrom(1024)
    msg = data.decode()
    
    # DISCOVERY
    if msg == "DISCOVERY":
        if addr not in tabela_clientes:
            # Cria cliente na tabela
            # USAR UNSIGNED INT de 64 bits
            tabela_clientes[addr] = {
                "last_req": 0,
                "last_num_reqs": 0,
                "last_total_sum": 0
            }
            # Envia resposta ao cliente
            resposta = f"{socket.gethostbyname(socket.gethostname())}"
            servidor.sendto(resposta.encode(), addr)
            print(f"Discovery respondido para {addr}")

    # PROCESSAMENTO
    else:
        try:
            # formato: req_id|numero
            req_user, numero = msg.split('|')
            req_user = int(req_user)
            numero = int(numero)

            # Consulta tabela para ver o id da última requisição do cliente
            ultima_requisicao = tabela_clientes[addr]["last_req"]

            # mensagem duplicada
            if req_user <= ultima_requisicao:
                imprimir_duplicada(tabela_clientes, addr, numero)
                continue

            # soma ao acumulador
            total += numero
            req_global += 1

            # Atualizar tabela clientes
            tabela_clientes[addr]["last_req"] = req_user
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
            print("Erro ao processar", e)
