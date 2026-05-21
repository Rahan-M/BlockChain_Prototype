import os
import json

BASE_STORAGE_DIR = os.path.dirname(os.path.abspath(__file__))

class StorageManager:

    def __init__(self, consensus, disk_load, disk_save):
        self.consensus = consensus
        self.disk_load = disk_load
        self.disk_save = disk_save

    def get_disk_load_status(self):
        return self.disk_load

    def get_disk_save_status(self):
        return self.disk_save
    
    def get_consensus_dir(self):
        """
        Returns the full path to the storage directory for the given consensus type.
        """
        path = os.path.join(BASE_STORAGE_DIR, self.consensus)
        os.makedirs(path, exist_ok=True)
        return path


    # == Node ID ===

    def save_node_id(self, node_id):
        path = os.path.join(self.get_consensus_dir(), "node_id.json")
        with open(path, 'w') as f:
            json.dump({
                "node_id": node_id
            }, f, indent=4)


    def load_node_id(self):
        path = os.path.join(self.get_consensus_dir(), "node_id.json")
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            data = json.load(f)
            return data.get("node_id")


    # === Keys ===

    def save_key(self, private_key_pem):
        path = os.path.join(self.get_consensus_dir(), "keys.json")
        with open(path, 'w') as f:
            json.dump({
                "private_key_pem": private_key_pem
            }, f, indent=4)


    def load_key(self):
        path = os.path.join(self.get_consensus_dir(), "keys.json")
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            data = json.load(f)
            return data.get("private_key_pem")


    # === Chain ===

    def save_chain(self, chain):
        path = os.path.join(self.get_consensus_dir(), "chain.json")
        with open(path, 'w') as f:
            json.dump(chain, f, indent=4)


    def load_chain(self):
        path = os.path.join(self.get_consensus_dir(), "chain.json")
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return json.load(f)


    # === Peers ===

    def save_peers(self, peer_list):
        path = os.path.join(self.get_consensus_dir(), "peers.json")
        with open(path, 'w') as f:
            json.dump(peer_list, f, indent=4)


    def load_peers(self):
        path = os.path.join(self.get_consensus_dir(), "peers.json")
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return json.load(f)