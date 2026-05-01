import threading
from conexao import automatic_input_thread, manual_input_thread, receive_thread


def entrada_por_arquivo(caminho_arquivo, client_socket, server_ip, server_port):
    t1 = threading.Thread(target=automatic_input_thread, args=(client_socket, server_ip, server_port, caminho_arquivo))
    t2 = threading.Thread(target=receive_thread, args=(client_socket,))

    t1.start()
    t2.start()

    t1.join()
    t2.join()


def entrada_manual(client_socket, server_ip, server_port):
    t1 = threading.Thread(target=manual_input_thread, args=(client_socket, server_ip, server_port))
    t2 = threading.Thread(target=receive_thread, args=(client_socket,))

    t1.start()
    t2.start()

    t1.join()
    t2.join()