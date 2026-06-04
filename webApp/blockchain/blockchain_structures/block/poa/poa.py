import json
import hashlib
import binascii

from typing import List

from ecdsa import VerifyingKey

from webApp.blockchain.blockchain_structures.transaction import Transaction
from webApp.blockchain.blockchain_structures.block.base import BaseBlock
from webApp.blockchain.blockchain_structures.utils import txs_to_json_digestable_form

class Block(BaseBlock):
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, id=None):
        super().__init__(prevHash, transactions, ts, id)
        self.miner_node_id= None
        self.miner_public_key= None
        self.signature = None # This will hold the digital signature from the miner
        self.miners_list = None # List of miner nodes

    def to_dict(self):
        return {
            "id":self.id,
            "prevHash":self.prevHash,
            "transactions":txs_to_json_digestable_form(self.transactions),
            "ts":self.ts,
            "miner_node_id":self.miner_node_id,
            "miner_public_key":self.miner_public_key,
            "miners_list":self.miners_list,
            "signature":self.signature,
            "files":self.files
        }

    def __str__(self):
        return json.dumps(self.to_dict())
    
    @property ## Now you can access hash like this myblock.hash
    def hash(self):
        block_str=json.dumps(self.to_dict())
        return hashlib.sha256(block_str.encode()).hexdigest()
      
    def get_message_to_sign(self):
        return json.dumps({
            "id": self.id,
            "ts": self.ts,
            "prevHash": self.prevHash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "miner_node_id": self.miner_node_id,
            "miner_public_key": self.miner_public_key,
            "miners_list": self.miners_list,
            "files":self.files
        }, sort_keys=True).encode()
    
    def is_valid_signature(self):
        try:
            # Load public key from PEM string
            public_key = VerifyingKey.from_pem(self.miner_public_key.encode())

            message = self.get_message_to_sign()
            signature = binascii.unhexlify(self.signature)

            public_key.verify(signature, message)
            print("\nValid Block\n")
            return True
        except Exception as e:
            print(f"Invalid block signature: {e}")
            return False