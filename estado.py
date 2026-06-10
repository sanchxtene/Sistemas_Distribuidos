# estado.py
import threading
import numpy as np

class ServidorState:
    def __init__(self):
        self.role = "BACKUP"

        self.rm_id = None
        self.primary_id = None
        self.primary_addr = None
        self.next_id = None

        self.members = {}

        self.req_global = 0
        self.total = np.uint64(0)

        self.tabela_clientes = {}

        self.tabela_servidor = {
            "num_reqs": 0,
            "total_sum": np.uint64(0)
        }

        self.state_lock = threading.Lock()
        self.membership_lock = threading.Lock()