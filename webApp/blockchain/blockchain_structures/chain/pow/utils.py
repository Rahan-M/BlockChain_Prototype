from typing import List

from ecdsa import (
    VerifyingKey,
    BadSignatureError
)

from webApp.blockchain.blockchain_structures.block.pow.pow import Block
from webApp.blockchain.blockchain_structures.transaction import Transaction

from webApp.blockchain.blockchain_structures.utils import valid_chain_length

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

def transaction_exists_in_block_list(
    blockList: List[Block],
    transaction_tc: Transaction,
    idx: int
):
    for i in range(idx):
        currBlock = blockList[i]

        for transaction in currBlock.transactions:
            if transaction.id == transaction_tc.id:
                return True

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
                vk_tx.verify(sign, transaction.to_string(include_signature=False).encode())
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