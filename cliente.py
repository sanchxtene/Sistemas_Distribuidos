import sys
import socket
from processamento_manual import teste_manual
from processamento_automatico import teste_arquivo
from conectar import conectar_com_servidor



# Configuração da porta servidor passada por parâmetro
if len(sys.argv) < 2:
    print("Erro - Falta de Parametros - Entrada deve ser: python cliente.py <PORTA>")
    exit()
porta = int(sys.argv[1])

# Configuração do servidor
# BROADCAST_IP = '255.255.255.255'
BROADCAST_IP = "127.0.0.1"

# Cria socket UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Broadcast
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Descoberta
client_socket.sendto(b"DISCOVERY", (BROADCAST_IP, porta))

# ADD settimeout e tentar novamente se não funcionar?

# IP do servidor
SERVER_IP = conectar_com_servidor(client_socket)

# ----- Processamento -----
# Numero máximo de tentativas por erro de timeout ajustável no arquivo "processamento.py"

# TESTANDO COM ARQUIVOS DE TESTE
#caminho_arquivo = ("RAND_NUM_1.txt")
#teste_arquivo(caminho_arquivo, client_socket, SERVER_IP, PROCESS_PORT)

# TESTANDO À MÃO
teste_manual(client_socket, SERVER_IP, porta)
