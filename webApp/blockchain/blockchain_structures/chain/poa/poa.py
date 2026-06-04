from typing import List

from ecdsa import (
    VerifyingKey,
    BadSignatureError
)

from webApp.blockchain.blockchain_structures.chain.base import CommonChain

from webApp.blockchain.blockchain_structures.block.poa.poa import Block
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

    def mine(self, block:Block): # point 1
        pass
    
    def rewrite(self, blockList :List[Block]):
        self.chain=blockList.copy()
                
    def isValidBlock(self, block: Block, reqd_miner_node_id, reqd_miner_public_key):
        if block.miner_node_id != reqd_miner_node_id:
            print("Mined by malicious miner")
            return False
        if self.lastBlock.hash!=block.prevHash:
            print("Hash Problem")
            print(f"Actual prev hash: {self.lastBlock.hash}\nMy prev hash: {block.prevHash}")
            return False
        
        mem_pool=[]
        for transaction in block.transactions:
            if self.transaction_exists_in_chain(transaction):
                print("Duplicate transaction(s)")
                return False
            sign_bytes=transaction.sign
            try:
                public_key=VerifyingKey.from_pem(transaction.sender.encode())
                public_key.verify(sign_bytes, str(transaction).encode())
            except:
                print("\nInvalid Signature On Transaction\n")
                return False
            
            amount = 0
            if transaction.receiver in ("deploy", "invoke"):
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if amount>self.calc_balance(publicKey=transaction.sender,pending_transactions=mem_pool) or amount<=0: 
                # we have to make sure the current transactions are included when checking for balance
                return False
            mem_pool.append(transaction)

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
            for transaction in (self.chain[i]).transactions:
                if transaction.sender==publicKey:
                    if transaction.receiver in ("deploy", "invoke"):
                        bal-=transaction.payload[-1]
                    else:
                        bal-=transaction.payload
                elif transaction.receiver==publicKey:
                    bal+=transaction.payload
            if self.chain[i].miner_public_key==publicKey:
                bal+=6 #Miner reward
        
        # Since these transactions arevalid not part of the chain we don't add
        # the money they gained yet because it could be invalid, but we subtract
        # the amount they have given to prevent double spending before the
        # transactions are added to the chain
        if pending_transactions:
            for transaction in pending_transactions:
                if transaction.sender==publicKey:
                    if transaction.receiver in ("deploy", "invoke"):
                        bal-=transaction.payload[-1]
                    else:
                        bal-=transaction.payload
        return bal