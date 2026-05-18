import json, hashlib, uuid, base64
from typing import List, Dict
from datetime import datetime
from ecdsa import SigningKey, SECP256k1, VerifyingKey, BadSignatureError
from shared_blockchain_structures import (
    Transaction,
    BaseBlock,
    CommonChain,
    Wallet,
    txs_to_json_digestable_form,
    valid_chain_length,
    transaction_exists_in_block_list
)

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

class Chain(CommonChain):
    instance =None #Class Variable

    def __init__(self, publicKey:str=None, blockList: List[Block]=None):
        """
            If we are the first node, we mine the genesis block for ouself
            otherwise we receive blockList from the bootstrap node and
            we assign that to be the chain
        """
        if Chain.instance is not None:
            return
        
        Chain.instance=self
        """
            If blocklist is given we simply make that the chain otherwise
            we create a new chain
        """

        if publicKey and not blockList:
            genesis_block = Block(None, [Transaction(50, "Genesis", publicKey)])
            super().__init__(genesis_block=genesis_block)
            self.mine(self.chain[0])
            
        elif blockList and not publicKey:
            super().__init__(block_list=blockList)

        else:
            raise ValueError("Invalid arguments")

        Chain.instance = self

    def mine(self, block:Block):
        block.nonce=0
        print("Mining...")
        
        while not block.hash.startswith("00000") :
            block.nonce+=1

        print(f"Solution Found!!! nonce = {block.nonce} hash = {block.hash}") 
        return block.nonce
   
    def rewrite(self, blockList :List[Block]):
        if len(self.chain)>=len(blockList):
            return
        
        Chain.instance.chain=blockList.copy()
              
    def isValidBlock(self, block: Block):
        #Verify Pow:
        if not block.hash.startswith("00000"):
            print(f"Problem with pow hash = {block.hash} nonce={block.nonce}")
            return False

        if self.lastBlock.hash!=block.prevHash:
            print("Hash Problem")
            print(f"Actual prev hash: {self.lastBlock.hash}\nMy prev hash: {block.prevHash}")
            return False
        
        mem_pool:List[Transaction]=[]
        for transaction in block.transactions:
            if Chain.instance.transaction_exists_in_chain(transaction):
                print("Duplicate transaction(s)")
                return False
            
            vk_tx=VerifyingKey.from_pem(transaction.sender.encode())
            try:
                vk_tx.verify(transaction.sign, str(transaction).encode())
            except:
                print("\nInvalid signature on transaction\n")
                return False
            
            amount = 0
            if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if amount>Chain.instance.calc_balance(publicKey=transaction.sender,pending_transactions=mem_pool or amount<0): 
                # we have to make sure the current transactions are included when checking for balance
                return False
            mem_pool.append(transaction)

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
            if Chain.instance.chain[i].miner==publicKey:
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
    
def calc_balance_block_list(block_list:List[Block], publicKey, i, pending_transactions:List[Transaction]=None):
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
        if block_list[i].miner==publicKey:
            bal+=6 #Miner reward

    if pending_transactions:
        for transaction in pending_transactions:
            if transaction.sender==publicKey:
                if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                    bal-=transaction.payload[-1]
                else:
                    bal-=transaction.payload
    return bal

def transaction_exists_in_block_list(blockList:List[Block], transaction_tc:Transaction, idx):
    for i in range(idx-1):
        currBlock=blockList[i]
        for transaction in currBlock.transactions:
            if(transaction.id==transaction_tc.id): 
                # We sign the id of the transaction, 
                # if it was truly a duplicate transaction
                # meant to reuse a sign then id must be the same
                # otherwise we'll get the invalid sign error
                return False

def isvalidChain(blockList:List[Block]):
    for i in range(len(blockList)):
        currBlock=blockList[i]        
        if(i<=0):
            continue
   
        if not currBlock.hash.startswith("00000"):
            print("\nNo POW\n")
            return False
        print("\nPow Done  and ")
        
        if(currBlock.prevHash!=blockList[i-1].hash):
            print("\n but Prev hash is incorrect\n")
            return False
        
        print("Prev hash is correct ")

        mem_pool=[]
        for transaction in blockList[i].transactions:
            sign=transaction.sign
            vk_tx=VerifyingKey.from_pem(transaction.sender.encode())
            if(transaction_exists_in_block_list(blockList, transaction, i)):
                print("Duplicate transaction(s)")
                return False
            try:
                vk_tx.verify(sign, str(transaction).encode())
            except:
                print("\nInvalid signature on transaction\n")
                return False

            amount = 0
            if(transaction.receiver == "deploy" or transaction.receiver == "invoke"):
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if(calc_balance_block_list(blockList, transaction.sender, i, mem_pool) < amount or amount<=0):
                return False
            mem_pool.append(transaction)
        
    print("No Duplicate transactions, No Inalid Signatures, No transactions with an invalid amount\n")
    return True