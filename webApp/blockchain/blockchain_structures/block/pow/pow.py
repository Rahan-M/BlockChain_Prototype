import json
import hashlib

from typing import List

from webApp.blockchain.blockchain_structures.transaction import Transaction
from webApp.blockchain.blockchain_structures.block.base_block import BaseBlock

from webApp.blockchain.blockchain_structures.utils import txs_to_json_digestable_form

class Block(BaseBlock):
    # pow block doesn't require sign for checking whether a block is valid
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, nonce=None, id=None):
        super().__init__(prevHash, transactions, ts, id)
        self.nonce=nonce or 0 
        self.miner: str=None

        

    def to_dict(self):
        return {
            "id":self.id,
            "prevHash":self.prevHash,
            "transactions":txs_to_json_digestable_form(self.transactions),
            "ts":self.ts,
            "nonce":self.nonce,
            "files":self.files
        }

    def __str__(self):
        return json.dumps(self.to_dict())
    
    @property ## Now you can access hash like this myblock.hash
    def hash(self):
        block_str=json.dumps(self.to_dict())
        return hashlib.sha256(block_str.encode()).hexdigest()