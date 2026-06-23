import threading

import conexao
from conexao import enviar_com_timeout, receive_thread, _destino


def _enviar_exit(sock):
    try:
        sock.sendto(b"EXIT", _destino())
    except Exception:
        pass


def _loop_teclado(sock):
    """Le numeros da entrada padrao e envia uma requisicao por vez.

    O id da requisicao comeca em 1 e e incrementado a cada envio confirmado.
    CTRL+D (EOF) ou CTRL+C encerram o cliente sinalizando EXIT ao servidor.
    """
    req_id = 0
    try:
        while conexao.running:
            entrada = input().strip()
            if not entrada:
                continue

            numero = int(entrada)
            req_id += 1

            if not enviar_com_timeout(sock, req_id, numero):
                break

    except (EOFError, KeyboardInterrupt):
        print("\nEncerrando cliente...")
    except ValueError:
        print("Entrada invalida; informe um numero inteiro.")
    finally:
        conexao.running = False
        _enviar_exit(sock)


def _loop_arquivo(sock, caminho_arquivo):
    """Le numeros de um arquivo (teste de volume), uma requisicao por vez."""
    req_id = 0
    try:
        with open(caminho_arquivo) as f:
            for linha in f:
                if not conexao.running:
                    break
                linha = linha.strip()
                if not linha:
                    continue

                numero = int(linha)
                req_id += 1

                if not enviar_com_timeout(sock, req_id, numero):
                    break
        print("\nFim do arquivo. Encerrando cliente...")
    except (EOFError, KeyboardInterrupt):
        print("\nEncerrando cliente...")
    finally:
        conexao.running = False
        _enviar_exit(sock)


def _iniciar(sock, porta, alvo, *args):
    """Sobe a thread de recepcao (escrita na tela) e executa o loop de envio
    na thread principal. Encerra ao terminar o loop de envio."""
    t_recv = threading.Thread(
        target=receive_thread,
        args=(sock, sock, porta),
        daemon=True,
    )
    t_recv.start()

    alvo(sock, *args)

    conexao.running = False
    t_recv.join(timeout=1)


def entrada_manual(sock, porta):
    _iniciar(sock, porta, _loop_teclado)


def entrada_por_arquivo(sock, porta, caminho_arquivo):
    _iniciar(sock, porta, _loop_arquivo, caminho_arquivo)
