# estado.py
import threading
import numpy as np
import time

class ServidorState:
    def __init__(self):
        self.role = "BACKUP"

        self.rm_id = None
        self.primary_id = None
        self.primary_addr = None
        self.next_id = None
        self.service_addr = None
        self.cluster_addr = None

        self.members = {}

        self.req_global = 0
        self.total = np.uint64(0)

        self.last_heartbeat = time.monotonic()
        self.election_in_progress = False
        self.election_ok_event = threading.Event()

        self.tabela_clientes = {}

        self.tabela_servidor = {
            "num_reqs": 0,
            "total_sum": np.uint64(0)
        }

        self.state_lock = threading.Lock()
        self.membership_lock = threading.Lock()