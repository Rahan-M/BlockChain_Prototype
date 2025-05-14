import json, random, hashlib, uuid
from typing import List
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


class Transaction:
    def __init__(self, amount: float, sender: str, receiver: str, id=None):
        self.id=id or str(uuid.uuid4())
        self.amount: float=amount
        self.sender: str=sender   # Public Key
        self.receiver: str=receiver   # Public Key


    def to_dict(self):
        dict={
            "id":self.id,
            "amount":self.amount,
            "sender":self.sender,
            "receiver":self.receiver
        }
        return dict
    
    def __eq__(self, other):
        return(
            self.id==other.id and
            self.amount==other.amount and
            self.sender==other.sender and
            self.receiver==other.receiver
        )
    
    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return json.dumps(self.to_dict())
    
def txs_to_json_digestable_form(transactions: List[Transaction]):
    l=[]
    for i in range(len(transactions)):
        l.append(transactions[i].to_dict())
    return l

class Block:
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, nonce=None, id=None):
        self.prevHash=prevHash
        self.transactions=transactions

        self.ts=ts or int(datetime.now().timestamp() * 1000)
        self.nonce=nonce or 0 #The _ are purely to make it easier on the eye

        self.id=id or str(uuid.uuid4())
        
        self.miner: str=None

    def to_dict(self):
        return {
            "id":self.id,
            "prevHash":self.prevHash,
            "transactions":txs_to_json_digestable_form(self.transactions),
            "ts":self.ts,
            "nonce":self.nonce
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
                sol=self.mine(self.chain[0])
                self.chain[0].solution=sol
            elif blockList and not publicKey:
                self.chain=blockList.copy()

    @property
    def lastBlock(self):
        return self.chain[-1]

    def mine(self, block:Block):
        block.nonce=0
        print("Mining...")
        
        while not block.hash.startswith("00000") :
            block.nonce+=1

        print(f"Solution Found!!! nonce = {block.nonce}")            

    def to_block_dict_list_with_sol(self):
        block_dict_list=[]
        for block in self.chain:
            block_dict_list.append(block.to_dict())
        
        return block_dict_list
    
    def rewrite(self, blockList :List[Block]):
        if len(self.chain)>=len(blockList):
            return
        
        Chain.instance.chain=blockList.copy()

    def addBlock(self, transactions: List[Transaction], senderPublicKey: str, signature: bytes):
        # Load public key, converts from string in PEM format to Bytes
        public_key=serialization.load_pem_public_key(senderPublicKey.encode())

        is_valid=False
        try:
            public_key.verify(
                signature,
                str(txs_to_json_digestable_form(transactions)).encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            is_valid=True
        except Exception as e:
            print(e)
            pass

        if is_valid:
            newBlock=Block(self.lastBlock.hash,transactions)
            solution=self.mine(newBlock.nonce)
            newBlock.solution=solution
            self.chain.append(newBlock)
            return newBlock
        else :
            return None

    def transaction_exists_in_chain(self, transaction: Transaction):
        for block in reversed(self.chain):
            if block.transaction_exists_in_block(transaction):
                return True
        
        return False
                
    def isValidBlock(self, block: Block):
        if self.lastBlock.hash!=block.prevHash:
            print("Hash Problem")
            print(f"{self.lastBlock.hash} \n\n {block.prevHash}")
            return False
        for transaction in block.transactions:
            if Chain.instance.transaction_exists_in_chain(transaction):
                print("Duplicate transaction(s)")
                return False
            
        #Verify Pow:
        if not block.hash.startswith("00000"):
            print("Problem with pow")
            return False

        return True

class Wallet:
    def __init__(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
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
    
    def sendMoney(self, amount: float, payeePublicKey:str):
        transaction=Transaction(amount, self.public_key, payeePublicKey)
        transactions=[transaction]
        transactions_data=str(txs_to_json_digestable_form(transactions)).encode()

        signature=self.private_key.sign(
            transactions_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        Chain.instance.addBlock(transactions, self.public_key, signature)
        return transaction

# Chain()

# rahan=Wallet()
# jefin=Wallet()
# elias=Wallet()

# tx1=rahan.sendMoney(50, jefin.public_key)
# tx2=jefin.sendMoney(30, elias.public_key)
# tx3=elias.sendMoney(60, rahan.public_key)

# print(tx1)
# print("\n\n")
# print(tranx)

# print(tx1==tranx)