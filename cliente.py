import sys
import socket
from processamento import entrada_por_arquivo, entrada_manual
from conexao import conectar_com_servidor

# Configuração do servidor
BROADCAST_IP = '255.255.255.255'
DISCOVERY_PORT = 3999

# Cria socket UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Broadcast
client_socket.settimeout(1)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Descoberta
client_socket.sendto(b"DISCOVERY", ("localhost", DISCOVERY_PORT))

client_socket.setblocking(True)

# IP do servidor
conectar_com_servidor(client_socket)

# ----- Processamento -----
# TESTANDO COM ARQUIVOS DE TESTE
caminho_arquivo = ("RAND_NUM_1.txt")
#entrada_por_arquivo(caminho_arquivo, client_socket)

# TESTANDO À MÃO
entrada_manual(client_socket)
