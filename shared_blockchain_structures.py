import json, uuid, base64
from typing import List, Dict 
from datetime import datetime
from ecdsa import VerifyingKey, SigningKey, SECP256k1

class Transaction:
    def __init__(self, payload, sender: str, receiver: str, id=None, ts=None):
        self.id=id or str(uuid.uuid4())
        self.payload=payload   # amount or [code, amount] or [contract id, function_name, arguments, state, amount]
        self.sender: str=sender  # Public Key
        self.receiver: str=receiver   # Public Key or "deploy" or "invoke"
        self.sign:bytes=None
        self.ts=ts or datetime.now().timestamp()

    def to_dict(self):
        dict={
            "id":self.id,
            "payload":self.payload,
            "sender":self.sender,
            "receiver":self.receiver,
            "ts":self.ts
        }
        return dict
    
    def __eq__(self, other):
        return(
            self.id==other.id and
            self.sender==other.sender and
            self.receiver==other.receiver and
            self.ts==other.ts
        )
    
    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return json.dumps(self.to_dict())
    
    def is_valid_signature(self):
        try:
            # Load public key from PEM string
            public_key = VerifyingKey.from_pem(self.sender.encode())

            message = str(self).encode()

            public_key.verify(self.sign, message)
            return True
        except Exception as e:
            print(f"Invalid transaction signature: {e}")
            return False
    
def txs_to_json_digestable_form(transactions: List[Transaction]):
    l=[]
    for i in range(len(transactions)):
        tx_dict=transactions[i].to_dict()
        if(transactions[i].sender!="Genesis"):
            tx_dict["sign"]=base64.b64encode(transactions[i].sign).decode()
        l.append(tx_dict)
    return l


class BaseBlock:
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, id=None):
        self.prevHash=prevHash
        self.transactions=transactions
        self.id=id or str(uuid.uuid4())
        self.ts=ts or int(datetime.now().timestamp() * 1000)
        self.files: Dict[str: str] = {}
    
    def transaction_exists_in_block(self, transaction: Transaction):
        for i in range(len(self.transactions)):
            if self.transactions[i]==transaction:
                return True
        return False

    def cid_exists_in_block(self, cid: str):
        for file_hash in list(self.files.keys()):
            if file_hash==cid:
                return True
        return False

class CommonChain:

    def __init__(self, genesis_block=None, block_list=None):

        if genesis_block is not None:
            self.chain = [genesis_block]
            print("Initializing Chain...")

        elif block_list is not None:
            self.chain = block_list.copy()

        else:
            raise ValueError("Invalid initialization")    @property
    def lastBlock(self):
        return self.chain[-1]

    
    @property
    def lastBlock(self):
        return self.chain[-1]
    
    def to_block_dict_list(self):
        block_dict_list=[]
        for block in self.chain:
            block_dict_list.append(block.to_dict())
        
        return block_dict_list

    def transaction_exists_in_chain(self, transaction: Transaction):
        for block in reversed(self.chain):
            if block.transaction_exists_in_block(transaction):
                return True
        
        return False

    def cid_exists_in_chain(self, cid: str):
        for block in reversed(self.chain):
            if block.cid_exists_in_block(cid):
                return True
        
        return False        


class Wallet:
    def __init__(self, private_key_pem: str = None):
        if not private_key_pem:
            self.private_key = SigningKey.generate(curve=SECP256k1)
        else:
            self.private_key = SigningKey.from_pem(private_key_pem)
            
        self.private_key_pem = self.private_key.to_pem().decode()

        self.public_key = self.private_key.get_verifying_key()

        self.public_key_pem = self.public_key.to_pem().decode()

def transaction_exists_in_block_list(blockList, transaction_tc:Transaction, idx):
    for i in range(idx-1):
        currBlock=blockList[i]
        for transaction in currBlock.transactions:
            if(transaction.id==transaction_tc.id): 
                # We sign the id of the transaction, 
                # if it was truly a duplicate transaction
                # meant to reuse a sign then id must be the same
                # otherwise we'll get the invalid sign error
                return False
            
def valid_chain_length(i):
    valid_chain_len=i # because we use zero indexing
    # We must be careful in how we choose which blocks are valid, since a block that was valid in before a new block is added shouldn't then become of undecided nature
    # i.e for exapmple when length is 9 say the first 7 blocks are considered valid then when length becomes 10, it shouldn't become 5 or something like that
    # For larger chains of length greater than 250 we assume blocks of depth greater than 50 is valid
    if(valid_chain_len<250):
        valid_chain_len=valid_chain_len-(valid_chain_len//5)
    else:
        valid_chain_len-=50
    return valid_chain_len 