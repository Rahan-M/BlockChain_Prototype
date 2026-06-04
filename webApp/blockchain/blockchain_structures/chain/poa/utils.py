from typing import List

from webApp.blockchain.blockchain_structures.block.poa.poa import Block
from webApp.blockchain.blockchain_structures.transaction import Transaction

from webApp.blockchain.blockchain_structures.utils import transaction_exists_in_block_list

def valid_chain_length(i):
    valid_chain_len=i # because we use zero indexing

    return valid_chain_len

def calc_balance_block_list(block_list:List[Block], publicKey, i, pending_transactions:List[Transaction]=None):
    bal=0
    valid_chain_len=valid_chain_length(i)

    for i in range(valid_chain_len):
        for transaction in (block_list[i]).transactions:
            if transaction.sender==publicKey:
                if transaction.receiver in ("deploy", "invoke"):
                    bal-=transaction.payload[-1]
                else:
                    bal-=transaction.payload
            elif transaction.receiver==publicKey:
                bal+=transaction.payload
                
        if block_list[i].miner_public_key==publicKey:
            bal+=6 #Miner reward
        
    if pending_transactions:
        for transaction in pending_transactions:
            if transaction.sender==publicKey:
                if transaction.receiver in ("deploy", "invoke"):
                    bal-=transaction.payload[-1]
                else:
                    bal-=transaction.payload

    # Since these transactions are not part of the chain we don't add
    # the money they gained yet because it could be invalid, but we subtract
    # the amount they have given to prevent double spending before the
    # transactions are added to the chain
    
    return bal

# Is valid chain function
def isvalidChain(blockList:List[Block]):
    for i in range(len(blockList)):
        currBlock=blockList[i]
        
        if(not currBlock.is_valid_signature()):
            return False
        
        if(i<=0):
            continue

        mem_pool=[]
        for transaction in blockList[i].transactions:
            sign=transaction.sign
            if not transaction.is_valid_signature():
                return False

            if(transaction_exists_in_block_list(blockList, transaction, i)):
                print("Duplicate transaction(s)")
                return False
            
            amount = 0
            if transaction.receiver in ("deploy", "invoke"):
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if(calc_balance_block_list(blockList, transaction.sender, i, mem_pool) < amount  or amount<=0):
                return False
            
            mem_pool.append(transaction)
               
        if (blockList[i].prevHash!=blockList[i-1].hash):
            return False

    return True