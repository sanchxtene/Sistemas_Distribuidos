import socket
import json

BROADCAST_IP = "255.255.255.255"

RM_DISCOVERY = "RM_DISCOVERY"
PRIMARY_HERE = "PRIMARY_HERE"

ROLE_PRIMARY = "PRIMARY"
ROLE_BACKUP = "BACKUP"

RM_PORTS = [
    4100,
    4101,
    4102,
    4103,
    4104
]

def descobrir_lider(sock, minha_porta):

  for porta in RM_PORTS:

    if porta == minha_porta:
        continue

    try:
        sock.sendto(
            b"RM_DISCOVERY",
            ("localhost", porta)
        )

        data, addr = sock.recvfrom(1024)

        msg = data.decode()

        if msg.startswith("PRIMARY_HERE"):
            return addr

    except socket.timeout:
        continue
  
    except ConnectionResetError:
        continue
    
    finally:
      sock.settimeout(None)

  return None


def criar_members_update(members):

  return json.dumps({
      "type": "MEMBERS_UPDATE",
      "members": members
  })


def enviar_members_update(sock, members):

    payload = {
        "type": "MEMBERS_UPDATE",
        "members": members
    }

    msg = f"CLUSTER|{json.dumps(payload)}"

    for rm_id, addr in members.items():

        try:
            sock.sendto(
                msg.encode(),
                addr
            )

        except:
            pass
        

def replicar_estado(sock, members, meu_id, req_global, total):

    payload = {
        "type": "STATE_UPDATE",
        "req_global": req_global,
        "total": int(total)
    }

    msg = f"CLUSTER|{json.dumps(payload)}"

    for rm_id, addr in members.items():

        if rm_id == meu_id:
            continue

        try:
            sock.sendto(
                msg.encode(),
                addr
            )

        except Exception as e:
            print(f"Erro ao replicar para RM {rm_id}: {e}")