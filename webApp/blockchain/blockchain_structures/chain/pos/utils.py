import hashlib

from datetime import datetime, timedelta

from typing import List

from ecdsa import (
    VerifyingKey,
    BadSignatureError
)

from webApp.blockchain.blockchain_structures.block.pos.pos import Block
from webApp.blockchain.blockchain_structures.transaction import Transaction
from webApp.blockchain.blockchain_structures.pos.stake import Stake

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

def weight_of_chain(block_list:List[Block]):
    total_weight=0
    for block in block_list:
        for stake in block.stakers:
            total_weight+=stake.amt
    return total_weight

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
    EPOCH_TIME = 60  # Add this constant or pass it as a parameter
    
    for i in range(len(blockList)):
        currBlock=blockList[i]
        vk=VerifyingKey.from_pem(currBlock.creator)
        try:
            vk.verify(currBlock.sign, str(currBlock).encode())
        except BadSignatureError:
            return False
        
        if(i<=0):
            continue

        # Timestamp validation
        try:
            # Convert Unix timestamp to datetime
            if isinstance(currBlock.ts, (int, float)):
                block_time = datetime.fromtimestamp(currBlock.ts)
            elif isinstance(currBlock.ts, str):
                block_time = datetime.fromisoformat(currBlock.ts)
            elif isinstance(currBlock.ts, datetime):
                block_time = currBlock.ts
            else:
                print("\nInvalid Block timestamp format\n")
                return False

            # Get previous block time
            prev_block_ts = blockList[i-1].ts
            if isinstance(prev_block_ts, (int, float)):
                prev_block_time = datetime.fromtimestamp(prev_block_ts)
            elif isinstance(prev_block_ts, str):
                prev_block_time = datetime.fromisoformat(prev_block_ts)
            elif isinstance(prev_block_ts, datetime):
                prev_block_time = prev_block_ts
            else:
                print("\nInvalid previous block timestamp format\n")
                return False

            # Check block isn't from the future (allow some tolerance for clock skew)
            current_time = datetime.now()
            if block_time > current_time + timedelta(seconds=10):
                print(f"\nBlock {i} timestamp in future\n")
                return False

            # Check blocks are in chronological order
            if block_time < prev_block_time:
                print(f"\nBlock {i} timestamp before previous block\n")
                return False

            # Verify minimum time between blocks (staking registration period)
            time_diff = (block_time - prev_block_time).total_seconds()
            if time_diff < EPOCH_TIME * 5/6:
                print(f"\nBlocks {i-1} and {i} too close together: {time_diff}s < {EPOCH_TIME * 5/6}s\n")
                return False

        except (ValueError, AttributeError, TypeError, OSError) as e:
            print(f"\nTimestamp validation error on block {i}: {e}\n")
            return False

        try:
            vk.verify(currBlock.vrf_proof, currBlock.seed.encode())
        except BadSignatureError:
            print("\nInvalid signature on vrf_proof\n")
            return False
        
        if(str(currBlock.seed)!=str(blockList[valid_chain_length(i)-1].hash)):
            print("\nInvalid Seed\n")
            return False

        total_stake=0
        for stake in currBlock.stakers:
            vk=VerifyingKey.from_pem(stake.staker)
            try:
                vk.verify(stake.sign, stake.to_string(include_signature=False).encode())
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
            if(transaction_exists_in_block_list(blockList, transaction, i)):
                print("Duplicate transaction(s)")
                return False
            
            sign=transaction.sign
            vk_tx=VerifyingKey.from_pem(transaction.sender)

            try:
                vk_tx.verify(sign, transaction.to_string(include_signature=False).encode())
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