import base64

from typing import List

from webApp.blockchain.blockchain_structures.transaction import Transaction

def txs_to_json_digestable_form(transactions: List[Transaction]):
    l=[]
    for i in range(len(transactions)):
        include_signature = True
        tx_dict = transactions[i].to_dict(include_signature)
        if(transactions[i].sender != "Genesis"):
            tx_dict["sign_b64"]=base64.b64encode(transactions[i].sign).decode()
            tx_dict.pop("sign", None)
        l.append(tx_dict)
    return l


def transaction_exists_in_block_list(
    blockList,
    transaction_tc: Transaction,
    idx: int
):
    for i in range(idx):

        currBlock = blockList[i]

        for transaction in currBlock.transactions:

            if transaction.id == transaction_tc.id:
                return True

    return False
            
def valid_chain_length(i):
    valid_chain_len=i # because we use zero indexing
    # We must be careful in how we choose which blocks are valid, since a block that was valid in before a new block is added shouldn't then become of undecided nature
    # i.e for exapmple when length is 9 say the first 7 blocks are considered valid then when length becomes 10, it shouldn't become 5 or something like that
    # For larger chains of length greater than 250 we assume blocks of depth greater than 50 is valid
    if(valid_chain_len<250):
        valid_chain_len=valid_chain_len-(valid_chain_len//5)
    else:
        valid_chain_len-=50
    return valid_chain_len 