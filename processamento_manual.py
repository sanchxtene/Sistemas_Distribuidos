import socket
from print_cliente import imprimir_retorno

MAX_TENTATIVAS = 3

def teste_manual(client_socket, server_ip, server_port):
    req_id = 0

    while True:
        entrada = input()

        try:
            numero = int(entrada)
            req_id += 1

            # Envia mensagem
            mensagem = f"{req_id}|{numero}"
            client_socket.sendto(mensagem.encode(), (server_ip, server_port))
            client_socket.settimeout(0.5)

            # ACK
            data, server_addr = client_socket.recvfrom(1024)
            msg = data.decode()
            _, id_req, _, value, _, num_reqs, _, total_sum = msg.split()
            imprimir_retorno(server_ip, id_req, value, num_reqs, total_sum)

        except:
            print("Erro")






"""
    req_id = 0

    while True:
        entrada = input("Digite um número inteiro positivo (ou 'sair'): ")

        if entrada.lower() == 'sair':
            break

        try:
            numero = int(entrada)

            if numero < 0:
                print(f"Digite apenas números positivos")
                continue

            req_id += 1

            tentativa = 0
            while tentativa < MAX_TENTATIVAS:
                mensagem = f"{req_id}|{numero}"
                print(f"ID da requisição: {req_id} | Valor enviado: {numero}")
                client_socket.sendto(mensagem.encode(), (SERVER_IP, PORT))
                client_socket.settimeout(0.01)

                try:
                    data, _ = client_socket.recvfrom(1024)
                    resposta = data.decode()

                    resp_id, status, valor = resposta.split('|')

                    if resp_id != str(req_id):
                        print("Resposta fora de ordem, ignorando...")
                        continue

                    print(f"Resposta: status={status}, acumulador={valor}")
                    break  # sucesso → sai do loop

                except socket.timeout:
                    tentativa += 1
                    print(f"Timeout, reenviando pacote ({tentativa}/{MAX_TENTATIVAS})")

            else:
                # só entra aqui se TODAS tentativas falharem
                print(f"Servidor não respondeu após {tentativa} tentativas")

        except ValueError:
            print("Entrada inválida, digite um número positivo")

"""