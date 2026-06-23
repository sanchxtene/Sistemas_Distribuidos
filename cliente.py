import sys
import socket

from conexao import conectar_com_servidor
from processamento import entrada_manual, entrada_por_arquivo

# Porta de comunicacao recebida por parametro: python3 cliente.py 4000
if len(sys.argv) < 2:
    print("Erro - Falta de Parametros - Entrada deve ser: python cliente.py <PORTA>")
    sys.exit(1)

porta = int(sys.argv[1])

# Socket UDP do cliente, habilitado para broadcast (fase de descoberta).
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Fase de descoberta: localiza o servidor e imprime "server_addr <ip>".
if conectar_com_servidor(client_socket, porta) is None:
    sys.exit(1)

# Fase de processamento.
#   Modo manual (teclado), conforme a especificacao:
entrada_manual(client_socket, porta)

#   Modo arquivo (testes de volume): descomente e ajuste o caminho.
# entrada_por_arquivo(client_socket, porta, "RAND_NUM_1.txt")
