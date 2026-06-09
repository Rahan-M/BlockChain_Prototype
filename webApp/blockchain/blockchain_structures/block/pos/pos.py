import json
import hashlib
import base64

from typing import List, Dict, Optional

from webApp.blockchain.blockchain_structures.transaction import Transaction
from webApp.blockchain.blockchain_structures.pos.stake import Stake
from webApp.blockchain.blockchain_structures.block.base import BaseBlock

from webApp.blockchain.blockchain_structures.utils import txs_to_json_digestable_form

class Block(BaseBlock):
    def __init__(self, prevHash:str, transactions:List[Transaction], ts=None, id=None):
        super().__init__(prevHash, transactions, ts, id)

        self.creator: str=""
        self.staked_amt=0
        
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
            stake_dict=stake.to_dict(include_signature=False)
            if(stake.sign):
                stake_dict["sign_b64"]=base64.b64encode(stake.sign).decode()
            stakes_dict_list.append(stake_dict)

        block_dict["stakers"]=stakes_dict_list
        if(self.vrf_proof and self.seed):
            block_dict["vrf_proof_b64"]=base64.b64encode(self.vrf_proof).decode()
            block_dict["seed"]=self.seed
        return block_dict


    def __str__(self):
        return json.dumps(self.to_dict())
    
    def is_equal(self, other):

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
            self.creator==other.creator
    )

    @property ## Now you can access hash like this myblock.hash
    def hash(self):
        block_str=json.dumps(self.to_dict())
        return hashlib.sha256(block_str.encode()).hexdigest()