import base64

from typing import List

from ecdsa import (
    VerifyingKey,
    BadSignatureError
)

from webApp.blockchain.blockchain_structures.block.pos.pos import Block
from webApp.blockchain.blockchain_structures.transaction import Transaction
from webApp.blockchain.blockchain_structures.pos.stake import Stake

from webApp.blockchain.blockchain_structures.chain.base import CommonChain

from webApp.blockchain.blockchain_structures.utils import valid_chain_length

class Chain(CommonChain):

    def __init__(self, block_list: List[Block] = None):

        if not block_list:
            self.chain = []
            return

        self.chain = block_list.copy()

    def create_genesis_block(self, public_key, private_key):
        genesis_block = Block(None, [Transaction(50,"Genesis",public_key)])
        genesis_block.creator = public_key
        genesis_block.sign = private_key.sign(str(genesis_block).encode())
        self.chain = [genesis_block]

    def to_block_dict_list(self):
        block_dict_list=[]
        for block in self.chain:
            block_dict=block.to_dict_with_stakers()
            if block.sign:
                block_dict["sign"]=base64.b64encode(block.sign).decode()
                
            block_dict_list.append(block_dict)
        
        return block_dict_list
    
    def rewrite(self, blockList :List[Block]):
        self.chain = blockList.copy()    
    
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
            if self.transaction_exists_in_chain(transaction):
                print("Duplicate transaction(s)")
                return False
            sign=transaction.sign
            vk=VerifyingKey.from_pem(transaction.sender)
            try:
                vk.verify(sign, transaction.to_string(include_signature=False).encode())
            except:
                print("\nFake Transactions\n")
                return False
            
            amount = 0
            if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if amount>self.calc_balance(publicKey=transaction.sender,pending_transactions=mem_pool,current_stakes=block.stakers) or amount<=0: 
                # we have to make sure the current transactions are included when checking for balance
                return False
            mem_pool.append(transaction)

        currStakes=[]
        for stake in block.stakers:
            vk=VerifyingKey.from_pem(stake.staker)
            try:
                vk.verify(stake.sign, stake.to_string(include_signature=False).encode())
            except BadSignatureError:
                print("\nInvalid signature on stake\n")
                return False
            if(stake.amt<=0 or stake.amt>self.calc_balance(stake.staker, mem_pool, currStakes)):
                return False
            currStakes.append(stake)
        return True
 
    def calc_balance(self, publicKey, pending_transactions:List[Transaction]=None, current_stakes:List[Stake]=None):
        bal=0
        valid_chain_len=valid_chain_length(len(self.chain))

        for i in range(valid_chain_len):
            if self.chain[i].slash_creator and self.chain[i].creator==publicKey:
                bal-=self.chain[i].staked_amt
            if not self.chain[i].is_valid:
                continue
            
            for transaction in (self.chain[i]).transactions:
                if transaction.sender==publicKey:
                    if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                        bal-=transaction.payload[-1]
                    else:
                        bal-=transaction.payload
                elif transaction.receiver==publicKey:
                    bal+=transaction.payload
            if self.chain[i].creator==publicKey:
                bal+=6 #Miner reward

        if valid_chain_len<len(self.chain):
            for i in range(valid_chain_len, len(self.chain)):
                currBlock=self.chain[i]
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