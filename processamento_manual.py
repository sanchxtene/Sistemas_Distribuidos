from print_cliente import imprimir_retorno
from conectar import enviar_mensagem

def teste_manual(client_socket, server_ip, server_port, max_tentativas):
    req_id = 0

    while True:
        entrada = input()

        try:
            # Cria mensagem
            numero = int(entrada)
            req_id += 1
            mensagem = f"{req_id}|{numero}"
            
            # Envia mensagem, recebe resposta
            resposta = enviar_mensagem(client_socket, mensagem, server_ip, server_port, max_tentativas)

            if resposta is None:
                print("Servidor não respondeu")
                continue

            # Separa a resposta e salva valores em variáveis
            _, id_req, _, value, _, num_reqs, _, total_sum = resposta.split()
            imprimir_retorno(server_ip, id_req, value, num_reqs, total_sum)

        except ValueError:
            print("Digite um número válido")

        except Exception as e:
            print("Erro:", e)