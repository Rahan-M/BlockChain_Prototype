import os
import json

BASE_STORAGE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_consensus_dir(consensus):
    """
    Returns the full path to the storage directory for the given consensus type.
    """
    path = os.path.join(BASE_STORAGE_DIR, consensus)
    os.makedirs(path, exist_ok=True)
    return path


# == Node ID ===

def save_node_id(node_id, consensus):
    path = os.path.join(get_consensus_dir(consensus), "node_id.json")
    with open(path, 'w') as f:
        json.dump({
            "node_id": node_id
        }, f, indent=4)


def load_node_id(consensus):
    path = os.path.join(get_consensus_dir(consensus), "node_id.json")
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        data = json.load(f)
        return data.get("node_id")


# === Keys ===

def save_key(private_key_pem, consensus):
    path = os.path.join(get_consensus_dir(consensus), "keys.json")
    with open(path, 'w') as f:
        json.dump({
            "private_key_pem": private_key_pem
        }, f, indent=4)


def load_key(consensus):
    path = os.path.join(get_consensus_dir(consensus), "keys.json")
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        data = json.load(f)
        return data.get("private_key_pem")


# === Chain ===

def save_chain(chain, consensus):
    path = os.path.join(get_consensus_dir(consensus), "chain.json")
    with open(path, 'w') as f:
        json.dump(chain, f, indent=4)


def load_chain(consensus):
    path = os.path.join(get_consensus_dir(consensus), "chain.json")
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return json.load(f)


# === Peers ===

def save_peers(peer_list, consensus):
    path = os.path.join(get_consensus_dir(consensus), "peers.json")
    with open(path, 'w') as f:
        json.dump(peer_list, f, indent=4)


def load_peers(consensus):
    path = os.path.join(get_consensus_dir(consensus), "peers.json")
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return json.load(f)