from typing import List

from ecdsa import (
    VerifyingKey,
    BadSignatureError
)

from webApp.blockchain.blockchain_structures.chain.base import CommonChain

from webApp.blockchain.blockchain_structures.block.pow.pow import Block
from webApp.blockchain.blockchain_structures.transaction import Transaction

from webApp.blockchain.blockchain_structures.utils import valid_chain_length

class Chain(CommonChain):

    def __init__(self, block_list = None):

        if not block_list:
            self.chain = []
            return

        self.chain = block_list.copy()

    def create_genesis_block(self, public_key):
        genesis_block = Block(None, [Transaction(50, "Genesis", public_key)])
        self.chain = [genesis_block]
        self.mine(self.chain[0])

    def mine(self, block:Block):
        block.nonce=0
        print("Mining...")
        
        while not block.hash.startswith("00000") :
            block.nonce+=1

        print(f"Solution Found!!! nonce = {block.nonce} hash = {block.hash}") 
        return block.nonce
   
    def rewrite(self, blockList :List[Block]):
        self.chain=blockList.copy()
              
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
            if self.transaction_exists_in_chain(transaction):
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
            if amount>self.calc_balance(publicKey=transaction.sender,pending_transactions=mem_pool) or amount<0: 
                # we have to make sure the current transactions are included when checking for balance
                return False
            mem_pool.append(transaction)

        return True

    def calc_balance(self, publicKey, pending_transactions:List[Transaction]=None):
        bal=0
        valid_chain_len=valid_chain_length(len(self.chain))

        for i in range(valid_chain_len):
            for transaction in (self.chain[i]).transactions:
                if transaction.sender==publicKey:
                    if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                        bal-=transaction.payload[-1]
                    else:
                        bal-=transaction.payload
                elif transaction.receiver==publicKey:
                    bal+=transaction.payload
            if self.chain[i].miner==publicKey:
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