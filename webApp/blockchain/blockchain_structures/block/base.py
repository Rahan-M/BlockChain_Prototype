import uuid

from datetime import datetime
from typing import Dict, List

from webApp.blockchain.blockchain_structures.transaction import Transaction

class BaseBlock:
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, id=None):
        self.prevHash = prevHash
        self.transactions = transactions
        self.id = id or str(uuid.uuid4())
        self.ts = ts or datetime.now().timestamp()
        self.files: Dict[str, str] = {}
    
    def transaction_exists_in_block(self, transaction: Transaction):
        return transaction in self.transactions

    def cid_exists_in_block(self, cid: str):
        return cid in self.files