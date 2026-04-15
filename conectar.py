import socket
from print_cliente import imprimir_conexao 

MAX_TENTATIVAS = 3

def conectar_com_servidor (client_socket):
    try:
        tentativa = 0
        while tentativa < MAX_TENTATIVAS:
            try:
                data, server_addr = client_socket.recvfrom(1024)
                client_socket.settimeout(0.01)
                msg = data.decode()

                _, server_ip, _ = msg.split('|')

                imprimir_conexao(server_ip)
                break  # sucesso → sai do loop

            except socket.timeout:
                tentativa += 1
                print(f"Timeout... tentando conexão novamente ({tentativa}/{MAX_TENTATIVAS})")

        else:
            # só entra aqui se TODAS tentativas falharem
            print(f"Servidor não respondeu após {MAX_TENTATIVAS} tentativas")

    except socket.timeout:
        print("Nenhum servidor respondeu")
        exit()

    return server_addr[0]



