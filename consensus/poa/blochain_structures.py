import json, hashlib, uuid, base64
from typing import List, Dict
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import binascii

GAS_PRICE = 0.001 # coin per gas unit

class Transaction:
    def __init__(self, payload, sender: str, receiver: str, id=None, ts=None):
        self.id=id or str(uuid.uuid4())
        self.payload=payload # amount or [code, amount] or [contract id, function_name, arguments, state, amount]
        self.sender: str=sender   # Public Key
        self.receiver: str=receiver   # Public Key or "deploy" or "invoke"
        self.sign: bytes=None
        self.ts=ts or datetime.now().timestamp()

    def to_dict(self):
        dict={
            "id":self.id,
            "payload":self.payload,
            "sender":self.sender,
            "receiver":self.receiver,
            "timestamp":self.ts,
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
            public_key = serialization.load_pem_public_key(
                self.sender.encode(),
                backend=default_backend()
            )

            message = str(self).encode()

            public_key.verify(
                self.sign,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
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

class Block:
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, id=None):
        self.id=id or str(uuid.uuid4())
        self.ts=ts or int(datetime.now().timestamp() * 1000)
        self.prevHash=prevHash
        self.transactions=transactions
        self.miner_node_id= None
        self.miner_public_key= None
        self.signature = None # This will hold the digital signature from the miner
        self.miners_list = None # List of miner nodes
        self.files: Dict[str: str] = {}

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
            public_key = serialization.load_pem_public_key(
                self.miner_public_key.encode(),
                backend=default_backend()
            )

            message = self.get_message_to_sign()
            signature = binascii.unhexlify(self.signature)

            public_key.verify(
                signature,
                message,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            print("\nValid Block\n")
            return True
        except Exception as e:
            print(f"Invalid block signature: {e}")
            return False

def valid_chain_length(i):
    valid_chain_len=i # because we use zero indexing

    return valid_chain_len

def calc_balance_block_list(block_list:List[Block], publicKey, i):
    bal=0
    valid_chain_len=valid_chain_length(i)

    for i in range(valid_chain_len):
        for transaction in (block_list[i]).transactions:
            if transaction.sender==publicKey:
                if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                    bal-=transaction.payload[-1]
                else:
                    bal-=transaction.payload
            elif transaction.receiver==publicKey:
                bal+=transaction.payload
                
        if block_list[i].miner_public_key==publicKey:
            bal+=6 #Miner reward

    # Since these transactions are not part of the chain we don't add
    # the money they gained yet because it could be invalid, but we subtract
    # the amount they have given to prevent double spending before the
    # transactions are added to the chain
    return bal

class Chain:
    instance =None #Class Variable

    def __init__(self, publicKey:str=None, blockList: List[Block]=None):
        """
            If we are the first node, we mine the genesis block for ouself
            otherwise we receive blockList from the bootstrap node and
            we assign that to be the chain
        """
        if not Chain.instance:
            Chain.instance=self
            """
                If blocklist is given we simply make that the chain otherwise
                we create a new chain
            """

            if publicKey and not blockList:
                self.chain=[Block(None, [Transaction(50,"Genesis",publicKey)])]
                print("Initializing Chain...")
                
            elif blockList and not publicKey:
                self.chain=blockList.copy()

    @property
    def lastBlock(self):
        return self.chain[-1]

    def mine(self, block:Block): # point 1
        pass

    def to_block_dict_list(self):
        block_dict_list=[]
        for block in self.chain:
            block_dict_list.append(block.to_dict())
        
        return block_dict_list
    
    def rewrite(self, blockList :List[Block]):
        if len(self.chain)>=len(blockList):
            return
        
        Chain.instance.chain=blockList.copy()

    def cid_exists_in_chain(self, cid: str):
        for block in reversed(self.chain):
            if block.cid_exists_in_block(cid):
                return True
        
        return False

    def transaction_exists_in_chain(self, transaction: Transaction):
        for block in reversed(self.chain):
            if block.transaction_exists_in_block(transaction):
                return True
        
        return False
                
    def isValidBlock(self, block: Block, reqd_miner_node_id, reqd_miner_public_key):
        if block.miner_node_id != reqd_miner_node_id:
            print("Mined by malicious miner")
            return False
        if self.lastBlock.hash!=block.prevHash:
            print("Hash Problem")
            print(f"Actual prev hash: {self.lastBlock.hash}\nMy prev hash: {block.prevHash}")
            return False
        
        for transaction in block.transactions:
            if Chain.instance.transaction_exists_in_chain(transaction):
                print("Duplicate transaction(s)")
                return False
            sign_bytes=transaction.sign
            try:
                public_key=serialization.load_pem_public_key(transaction.sender.encode())
                public_key.verify(
                    sign_bytes,
                    str(transaction).encode(),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
            except:
                print("\nInvalid Signature On Transaction\n")
                return False

        if block.miner_public_key != reqd_miner_public_key:
            print("Invalid miner public key")
            return False
        
        if not block.is_valid_signature():
            print("\nInvalid Signature On Block\n")
            return False

        return True

    def calc_balance(self, publicKey, pending_transactions:List[Transaction]=None):
        bal=0
        valid_chain_len=valid_chain_length(len(self.chain))

        for i in range(valid_chain_len):
            for transaction in (Chain.instance.chain[i]).transactions:
                if transaction.sender==publicKey:
                    if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                        bal-=transaction.payload[-1]
                    else:
                        bal-=transaction.payload
                elif transaction.receiver==publicKey:
                    bal+=transaction.payload
            if Chain.instance.chain[i].miner_public_key==publicKey:
                bal+=6 #Miner reward
        
        # Since these transactions are not part of the chain we don't add
        # the money they gained yet because it could be invalid, but we subtract
        # the amount they have given to prevent double spending before the
        # transactions are added to the chain
        if pending_transactions:
            for transaction in pending_transactions:
                if transaction.sender==publicKey:
                    if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                        bal-=transaction.payload[-1]
                    else:
                        bal-=transaction.payload
        return bal

class Wallet:
    def __init__(self, private_key_pem: str = None):
        if not private_key_pem:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
        else:
            self.private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )

        self.private_key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()

        self.public_key = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()


# Is valid chain function
def isvalidChain(blockList:List[Block]):
    for i in range(len(blockList)):
        currBlock=blockList[i]
        
        if(not currBlock.is_valid_signature()):
            return False
        
        if(i<=0):
            continue


        for transaction in blockList[i].transactions:
            sign=transaction.sign
            if not transaction.is_valid_signature():
                return False

            amount = 0
            if(transaction.receiver == "deploy" or transaction.receiver == "invoke"):
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if(calc_balance_block_list(blockList, transaction.sender, i) < amount):
                return False
               
        if (blockList[i].prevHash!=blockList[i-1].hash):
            return False

    return True
