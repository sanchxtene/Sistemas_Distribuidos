import socket
from print_cliente import imprimir_conexao 

max_tentativas = 3

def conectar_com_servidor (client_socket):
    tentativa = 0

    while tentativa < max_tentativas:
        try:
            # Servidor responde com o endereço IP
            data, server_addr = client_socket.recvfrom(1024)
            client_socket.settimeout(0.01)
            msg = data.decode()
            imprimir_conexao(msg)
            return server_addr[0]  # sucesso → sai do loop

        except socket.timeout:
            # Servidor não respondeu
            tentativa += 1
            print(f"Timeout... tentando conexão novamente ({tentativa}/{max_tentativas})")

    # TODAS as tentativas falharam
    print(f"Servidor não respondeu após {max_tentativas} tentativas")
    return None 