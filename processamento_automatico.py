import socket

MAX_TENTATIVAS = 3

def teste_arquivo(caminho_arquivo, client_socket, SERVER_IP, PORT):
    req_id = 0

    with open(caminho_arquivo, 'r') as f:
        linhas = f.readlines()

    for linha in linhas:
        linha = linha.strip()

        if not linha:
            continue

        try:
            numero = int(linha)

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