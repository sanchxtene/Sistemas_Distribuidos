import sys
import socket
from processamento_manual import teste_manual
from processamento_automatico import teste_arquivo
from conexao import conectar_com_servidor



# Configuração da porta servidor passada por parâmetro
if len(sys.argv) < 2:
    print("Erro - Falta de Parametros - Entrada deve ser: python cliente.py <PORTA>")
    exit()
porta = int(sys.argv[1])

# Configuração do servidor
BROADCAST_IP = '255.255.255.255'

# Cria socket UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Broadcast
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Descoberta
client_socket.sendto(b"DISCOVERY", (BROADCAST_IP, porta))

# IP do servidor
SERVER_IP = conectar_com_servidor(client_socket)

"""
A interface do cliente deve ter uma thread para escrever as mensagens na tela, e outra thread para ler os
comandos digitados pelo(a) usuário(a). Ao apertar CTRL+C (interrupção) ou CTRL+D (fim de arquivo), o processo
cliente deverá encerrar, sinalizando ao manager que o(a) usuário(a) está saindo do serviço (similar a EXIT)
"""

# ----- Processamento -----
# TESTANDO COM ARQUIVOS DE TESTE
caminho_arquivo = ("RAND_NUM_4.txt")
teste_arquivo(caminho_arquivo, client_socket, SERVER_IP, porta)

# TESTANDO À MÃO
#teste_manual(client_socket, SERVER_IP, porta)
