import sys
import socket
from processamento import entrada_por_arquivo, entrada_manual
from conexao import conectar_com_servidor

# Configuração da porta servidor passada por parâmetro
if len(sys.argv) < 2:
    print("Erro - Falta de Parametros - Entrada deve ser: python cliente.py <PORTA>")
    exit()
porta = int(sys.argv[1])

# Cria socket UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Broadcast
BROADCAST_IP = '255.255.255.255'
client_socket.settimeout(1)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
client_socket.sendto(b"DISCOVERY", (BROADCAST_IP, porta))
client_socket.setblocking(True)

# Conectar com servidor primário
conectar_com_servidor(client_socket)

# ----- Processamento -----
# TESTANDO COM ARQUIVOS DE TESTE
caminho_arquivo = ("RAND_NUM_1.txt")
#entrada_por_arquivo(caminho_arquivo, client_socket)

# TESTANDO À MÃO
entrada_manual(client_socket)
