import json, hashlib, uuid, base64
from typing import List,Dict
from datetime import datetime
from ecdsa import SigningKey, SECP256k1, VerifyingKey, BadSignatureError

GAS_PRICE = 0.001 # coin per gas unit
MAX_OUTPUT=2**256

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
    
def txs_to_json_digestable_form(transactions: List[Transaction]):
    l=[]
    for i in range(len(transactions)):
        tx_dict=transactions[i].to_dict()
        if(transactions[i].sender!="Genesis"):
            tx_dict["sign"]=base64.b64encode(transactions[i].sign).decode()
        l.append(tx_dict)
    return l

class Stake:
    def __init__(self, staker:str, amt:float, ts=None):
        self.id=str(uuid.uuid4())
        self.staker=staker
        self.amt=amt
        self.sign:bytes=None

        self.ts=ts or datetime.now().timestamp()

    def to_dict(self):
        return {
            "id":self.id,
            "staker":self.staker,
            "amt":self.amt,
            "ts":self.ts
        }

    def __str__(self):
        return json.dumps(self.to_dict())
    
class Block:
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, id=None):
        self.prevHash=prevHash
        self.transactions=transactions
        self.ts=ts or datetime.now().timestamp()
        self.id=id or str(uuid.uuid4())
        self.creator: str=""
        self.staked_amt=0
        self.files: Dict[str: str] = {}
        
        self.stakers:List[Stake]=[]  # needs to be replaced everywhere with stakes
        self.seed:str=""
        self.vrf_proof:bytes=None
        self.sign: bytes=None
        self.is_valid:bool=True
        self.slash_creator=False

    def to_dict(self):
        return {
            "id":self.id,
            "prevHash":self.prevHash,
            "transactions":txs_to_json_digestable_form(self.transactions),
            "ts":self.ts,
            "creator":self.creator,
            "staked_amt":self.staked_amt,
            "files":self.files
        }
    
    def to_dict_with_stakers(self):
        block_dict=self.to_dict()
        
        stakes_dict_list:List[Dict]=[]
        for stake in self.stakers:
            stake_dict=stake.to_dict()
            if(stake.sign):
                stake_dict["sign"]=base64.b64encode(stake.sign).decode()
            stakes_dict_list.append(stake_dict)

        block_dict["stakers"]=stakes_dict_list
        if(self.vrf_proof and self.seed):
            block_dict["vrf_proof_b64"]=base64.b64encode(self.vrf_proof).decode()
            block_dict["seed"]=self.seed
        return block_dict


    def __str__(self):
        return json.dumps(self.to_dict())
    
    def is_equal(self, other):
        same=True
        if(len(self.transactions)!=len(other.transactions)):
            return False
        
        tx_len=len(self.transactions)
        for i in range(tx_len):
            if(self.transactions[i]!=other.transactions[i]):
                return False
            
        return(
            self.id==other.id and
            self.ts==other.ts and
            self.prevHash==other.prevHash and
            self.hash==other.hash and
            self.sign==other.sign and
            self.creator==self.creator
    )

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

    if(valid_chain_len<250):
        valid_chain_len=valid_chain_len-(valid_chain_len//5)
    else:
        valid_chain_len-=50
    return valid_chain_len  

def calc_balance_block_list(block_list:List[Block], publicKey, i, mem_pool:List[Transaction]=None, currStakes:List[Stake]=None):
    bal=0
    valid_chain_len=valid_chain_length(i)

    for i in range(valid_chain_len):
        if block_list[i].slash_creator and block_list[i].creator==publicKey:
            bal-=block_list[i].staked_amt
        if not block_list[i].is_valid:
            continue
        
        for transaction in (block_list[i]).transactions:
            if transaction.sender==publicKey:
                if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                    bal-=transaction.payload[-1]
                else:
                    bal-=transaction.payload
            elif transaction.receiver==publicKey:
                bal+=transaction.payload
        if block_list[i].creator==publicKey:
            bal+=6 #Miner reward
    
    for transaction in mem_pool:
        if transaction.sender==publicKey:
            if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                bal-=transaction.payload[-1]
            else:
                bal-=transaction.payload

    if currStakes:
        for stake in currStakes:
            if stake.staker==publicKey:
                bal-=stake.amt
    # Since these transactions are not part of the chain we don't add
    # the money they gained yet because it could be invalid, but we subtract
    # the amount they have given to prevent double spending before the
    # transactions are added to the chain
    return bal

class Chain:
    instance =None #Class Variable

    def __init__(self, publicKey:str=None, privatekey=None, blockList: List[Block]=None):
        """
            If we are the first node, we mine the genesis block for ourself
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
                genesis_block=Block(None, [Transaction(50,"Genesis",publicKey)])
                genesis_block.creator=publicKey
                genesis_block.sign=privatekey.sign(str(genesis_block).encode())
                self.chain=[genesis_block]

                print("Initializing Chain...")
                
            elif blockList and not publicKey:
                self.chain=blockList.copy() 

    @property
    def lastBlock(self):
        return self.chain[-1]

    def to_block_dict_list(self):
        block_dict_list=[]
        for block in self.chain:
            block_dict=block.to_dict_with_stakers()
            if block.sign:
                block_dict["sign"]=base64.b64encode(block.sign).decode()
                
            block_dict_list.append(block_dict)
        
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
        mem_pool=[] 
        # if we don't store this then a person can send two valid transaction 
        # less than his acc balance but the sum of it could be greater 
        # than his account balance
        for transaction in block.transactions:
            if Chain.instance.transaction_exists_in_chain(transaction):
                print("Duplicate transaction(s)")
                return False
            sign=transaction.sign
            vk=VerifyingKey.from_pem(transaction.sender)
            try:
                vk.verify(sign, str(transaction).encode())
            except:
                print("\nFake Transactions\n")
                return False
            
            amount = 0
            if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if amount>Chain.instance.calc_balance(publicKey=transaction.sender,pending_transactions=mem_pool,current_stakes=block.stakers) or amount<=0: 
                # we have to make sure the current transactions are included when checking for balance
                return False
            mem_pool.append(transaction)

        currStakes=[]
        for stake in block.stakers:
            vk=VerifyingKey.from_pem(stake.staker)
            try:
                vk.verify(stake.sign, str(stake).encode())
            except BadSignatureError:
                print("\nInvalid signature on stake\n")
                return False
            if(stake.amt<=0 or stake.amt>Chain.instance.calc_balance(stake.staker, mem_pool, currStakes)):
                return False
            currStakes.append(stake)
        return True
 
    def calc_balance(self, publicKey, pending_transactions:List[Transaction]=None, current_stakes:List[Stake]=None):
        bal=0
        valid_chain_len=valid_chain_length(len(self.chain))

        for i in range(valid_chain_len):
            if Chain.instance.chain[i].slash_creator and Chain.instance.chain[i].creator==publicKey:
                bal-=Chain.instance.chain[i].staked_amt
            if not Chain.instance.chain[i].is_valid:
                continue
            
            for transaction in (Chain.instance.chain[i]).transactions:
                if transaction.sender==publicKey:
                    if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                        bal-=transaction.payload[-1]
                    else:
                        bal-=transaction.payload
                elif transaction.receiver==publicKey:
                    bal+=transaction.payload
            if Chain.instance.chain[i].creator==publicKey:
                bal+=6 #Miner reward

        if valid_chain_len<len(self.chain):
            for i in range(valid_chain_len, len(self.chain)):
                currBlock=Chain.instance.chain[i]
                for transaction in currBlock.transactions:
                    if transaction.sender==publicKey:
                        if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                            bal-=transaction.payload[-1]
                        else:
                            bal-=transaction.payload
        
        if current_stakes:
            for stake in current_stakes:
                if stake.staker==publicKey:
                    bal-=stake.amt

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

    def epoch_seed(self):
        bal=0
        last_finalized_block_hash=self.chain[valid_chain_length(len(self.chain))-1].hash
        return last_finalized_block_hash

    def checkEquivalence(self, block_list:List[Block]):
        """
            Returns -1 if there is no divergence, returns index of divergence if there is any
        """
        min_len=min(len(self.chain), len(block_list))
        for i in range(min_len):
            if(not self.chain[i].is_equal(block_list[i])):
                return i
        return -1

class Wallet:
    def __init__(self, private_key_pem: str = None):
        if not private_key_pem:
            self.private_key = SigningKey.generate(curve=SECP256k1)
        else:
            self.private_key = SigningKey.from_pem(private_key_pem)
            
        self.private_key_pem = self.private_key.to_pem().decode()

        self.public_key = self.private_key.get_verifying_key()

        self.public_key_pem = self.public_key.to_pem().decode()

def transaction_exists_in_block_list(blockList:List[Block], transaction_tc:Transaction, idx):
    for i in range(idx-1):
        currBlock=blockList[i]
        for transaction in currBlock:
            if(transaction.id==transaction_tc.id): 
                # We sign the id of the transaction, 
                # if it was truly a duplicate transaction
                # meant to reuse a sign then id must be the same
                # otherwise we'll get the invalid sign error
                return False

def isvalidChain(blockList:List[Block]):
    for i in range(len(blockList)):
        currBlock=blockList[i]
        vk=VerifyingKey.from_pem(currBlock.creator)
        try:
            vk.verify(currBlock.sign, str(currBlock).encode())
        except BadSignatureError:
            return False
        
        if(i<=0):
            continue

        try:
            vk.verify(currBlock.vrf_proof, currBlock.seed.encode())
        except BadSignatureError:
            print("\nInvalid signature on vrf_proof\n")
            return False
        
        if(str(currBlock.seed)!=str(blockList[valid_chain_length(i)-1].hash)):
            print("\nInvalid Seed\n")
            return False

        if(transaction_exists_in_block_list(blockList, transaction, i)):
            print("Duplicate transaction(s)")
            return False

        total_stake=0
        for stake in currBlock.stakers:
            vk=VerifyingKey.from_pem(stake.staker)
            try:
                vk.verify(stake.sign, str(stake).encode())
            except BadSignatureError:
                print("\nInvalid signature on stake\n")
                return False
            if(stake.amt<=0):
                return False
            total_stake+=stake.amt

        vrf_output=hashlib.sha256(currBlock.vrf_proof).hexdigest()
        vrf_ouput_int=int(vrf_output, 16)

        threshold=(currBlock.staked_amt/total_stake)*MAX_OUTPUT
        if(vrf_ouput_int>threshold):
            print("\nFalsified vrf\n")
            return False

        mem_pool=[]
        for transaction in blockList[i].transactions:
            sign=transaction.sign
            vk_tx=VerifyingKey.from_pem(transaction.sender)

            try:
                vk_tx.verify(sign, str(transaction).encode())
            except BadSignatureError:
                print("\nInvalid signature on transaction\n")
                return False

            amount = 0
            if(transaction.receiver == "deploy" or transaction.receiver == "invoke"):
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if(calc_balance_block_list(blockList, transaction.sender, i, mem_pool, currBlock.stakers) < amount or amount<=0):
                return False
            mem_pool.append(transaction)
        
        # we use a currStakes list because if we just pass currBlock.stakers then the stake 
        # which we are processing will already be there
        currStakes=[]
        for stake in currBlock.stakers:
            if stake.amt>calc_balance_block_list(blockList, stake.staker, i, mem_pool, currStakes):
                return False
            currStakes.append(stake)

        
        if(calc_balance_block_list(blockList, blockList[i].creator, i, mem_pool)<0):
            return False
        
        if (blockList[i].prevHash!=blockList[i-1].hash):
            return False

    return True

def weight_of_chain(block_list:List[Block]):
    total_weight=0
    for block in block_list:
        for stake in block.stakers:
            total_weight+=stake.amt
    return total_weight