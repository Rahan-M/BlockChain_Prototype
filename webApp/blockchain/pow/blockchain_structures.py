import json, hashlib, uuid, base64
from typing import List, Dict
from datetime import datetime
from ecdsa import SigningKey, SECP256k1, VerifyingKey, BadSignatureError

class Transaction:
    def __init__(self, amount: float, sender: str, receiver: str, id=None, ts=None):
        self.id=id or str(uuid.uuid4())
        self.amount: float=amount
        self.sender: str=sender   # Public Key
        self.receiver: str=receiver   # Public Key

        self.sign:bytes=None
        self.ts=ts or datetime.now().timestamp()

    def to_dict(self):
        dict={
            "id":self.id,
            "amount":self.amount,
            "sender":self.sender,
            "receiver":self.receiver,
            "ts":self.ts
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
        tx_dict=transactions[i].to_dict()
        if(transactions[i].sender!="Genesis"):
            tx_dict["sign"]=base64.b64encode(transactions[i].sign).decode()
        l.append(tx_dict)
    return l

class Block:
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, nonce=None, id=None):
        self.prevHash=prevHash
        self.transactions=transactions

        self.ts=ts or int(datetime.now().timestamp() * 1000)
        self.nonce=nonce or 0 #The _ are purely to make it easier on the eye

        self.id=id or str(uuid.uuid4())
        
        self.miner: str=None
        self.files: Dict[str: str] = {}

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


def valid_chain_length(i):
    valid_chain_len=i # because we use zero indexing4

    if valid_chain_len>=50:
        valid_chain_len-=10
    elif valid_chain_len>=25:
        valid_chain_len-=5
    elif valid_chain_len>=10:
        valid_chain_len-=3
    elif valid_chain_len>=5:
        valid_chain_len-=2
    return valid_chain_len 

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
                self.mine(self.chain[0])
                
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

        print(f"Solution Found!!! nonce = {block.nonce} hash = {block.hash}") 
        return block.nonce

    def to_block_dict_list(self):
        block_dict_list=[]
        for block in self.chain:
            block_dict_list.append(block.to_dict())
        
        return block_dict_list
    
    def rewrite(self, blockList :List[Block]):
        if len(self.chain)>=len(blockList):
            return
        
        Chain.instance.chain=blockList.copy()

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
                
    def isValidBlock(self, block: Block):
        if self.lastBlock.hash!=block.prevHash:
            print("Hash Problem")
            print(f"Actual prev hash: {self.lastBlock.hash}\nMy prev hash: {block.prevHash}")
            return False
        for transaction in block.transactions:

            if Chain.instance.transaction_exists_in_chain(transaction):
                print("Duplicate transaction(s)")
                return False
            
            sign=transaction.sign
            vk=VerifyingKey.from_pem(transaction.sender)
            try:
                vk.verify(sign, str(transaction).encode())
            except:
                print("\nInvalid signature on transaction\n")
                return False

        #Verify Pow:
        if not block.hash.startswith("00000"):
            print(f"Problem with pow hash = {block.hash} nonce={block.nonce}")

            return False

        return True

    def calc_balance(self, publicKey, pending_transactions:List[Transaction]=None):
        bal=0
        valid_chain_len=valid_chain_length(len(self.chain))

        for i in range(valid_chain_len):
            for transaction in (self.chain[i]).transactions:
                if transaction.sender==publicKey:   
                    bal-=transaction.amount
                elif transaction.receiver==publicKey:
                    bal+=transaction.amount
            if self.chain[i].miner==publicKey:
                bal+=6 #Miner reward
        
        # Since these transactions are not part of the chain we don't add
        # the money they gained yet because it could be invalid, but we subtract
        # the amount they have given to prevent double spending before the
        # transactions are added to the chain
        if pending_transactions:
            for transaction in pending_transactions:
                if transaction.sender==publicKey:
                    bal-=transaction.amount
        return bal

class Wallet:
    def __init__(self):
        self.private_key = SigningKey.generate(curve=SECP256k1)
        
        self.private_key_pem = self.private_key.to_pem().decode()

        self.public_key = self.private_key.get_verifying_key()

        self.public_key_pem = self.public_key.to_pem().decode()
    
def calc_balance_block_list(block_list:List[Block], publicKey, i):
    bal=0
    valid_chain_len=valid_chain_length(i)

    for i in range(valid_chain_len):
        for transaction in (block_list[i]).transactions:
            if transaction.sender==publicKey:   
                bal-=transaction.amount
            elif transaction.receiver==publicKey:
                bal+=transaction.amount
        if block_list[i].miner==publicKey:
            bal+=6 #Miner reward
        
    return bal

def isvalidChain(blockList:List[Block]):
    for i in range(len(blockList)):
        currBlock=blockList[i]        
        if(i<=0):
            continue
   
        if not currBlock.hash.startswith("00000"):
            return False

        for transaction in blockList[i].transactions:
            sign=transaction.sign
            vk_tx=VerifyingKey.from_pem(transaction.sender)

            try:
                vk_tx.verify(sign, str(transaction).encode())
            except BadSignatureError:
                print("\nInvalid signature on transaction\n")
                return False

            if(calc_balance_block_list(blockList, transaction.sender, i)<transaction.amount):
                return False
        
        if (blockList[i].prevHash!=blockList[i-1].hash):
            return False

    return True
