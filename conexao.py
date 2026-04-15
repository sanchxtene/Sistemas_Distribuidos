import socket
from print_cliente import imprimir_conexao 

def conectar_com_servidor (client_socket, max_tentativas):
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



def enviar_mensagem(client_socket, mensagem, server_ip, server_port, max_tentativas):
    tentativa = 0

    while tentativa < max_tentativas:
        client_socket.sendto(mensagem.encode(), (server_ip, server_port))
        client_socket.settimeout(0.01)

        try:
            data, _ = client_socket.recvfrom(1024)
            return data.decode() # sucesso → sai do loop

        except socket.timeout:
            # Servidor não respondeu
            tentativa += 1
            print(f"Timeout... tentando novamente ({tentativa}/{max_tentativas})")

    # TODAS as tentativas falharam
    return None