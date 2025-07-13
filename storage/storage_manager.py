import os
import json

STORAGE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(STORAGE_DIR, "keys.json")
CHAIN_FILE = os.path.join(STORAGE_DIR, "chain.json")
PEERS_FILE = os.path.join(STORAGE_DIR, "peers.json")


# === Keys ===

def save_key(private_key_pem):
    with open(KEYS_FILE, 'w') as f:
        json.dump({
            "private_key_pem": private_key_pem
        }, f, indent=4)


def load_key():
    if not os.path.exists(KEYS_FILE):
        return None
    with open(KEYS_FILE, 'r') as f:
        data = json.load(f)
        return data.get("private_key_pem")


# === Chain ===

def save_chain(chain):
    with open(CHAIN_FILE, 'w') as f:
        json.dump(chain, f, indent=4)


def load_chain():
    if not os.path.exists(CHAIN_FILE):
        return None
    with open(CHAIN_FILE, 'r') as f:
        return json.load(f)


# === Peers ===

def save_peers(peer_list):
    with open(PEERS_FILE, 'w') as f:
        json.dump(peer_list, f, indent=4)


def load_peers():
    if not os.path.exists(PEERS_FILE):
        return None
    with open(PEERS_FILE, 'r') as f:
        return json.load(f)