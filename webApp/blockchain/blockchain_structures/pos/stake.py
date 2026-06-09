import uuid
import json
import base64

from datetime import datetime
from typing import Optional

from ecdsa import VerifyingKey

class Stake:
    def __init__(self, staker:str, amt:int, id = None, ts = None, sign = None):
        self.id = id or str(uuid.uuid4())
        self.staker = staker
        self.amt = amt
        self.ts = ts or datetime.now().timestamp()
        self.sign:bytes = sign

    def to_dict(self, include_signature):
        data = {
            "id":self.id,
            "staker":self.staker,
            "amt":self.amt,
            "ts":self.ts
        }

        if include_signature:
            data["sign"] = self.sign

        return data

    def to_string(self, include_signature):
        data = self.to_dict(include_signature)

        if include_signature and data["sign"] is not None:
            data["sign_b64"] = base64.b64encode(data.pop("sign")).decode()

        return json.dumps(data, sort_keys=True)

    def sign_stake(self, private_key):

        include_signature = False
        stake_str = self.to_string(include_signature)

        signature = private_key.sign(stake_str.encode())

        self.sign = signature

    def is_valid_signature(self):

        try:
            public_key = VerifyingKey.from_pem(self.staker.encode())
            include_signature = False
            message = self.to_string(include_signature).encode()

            public_key.verify(self.sign, message)
            return True

        except Exception as e:
            print(f"Invalid transaction signature: {e}")
            return False

    def is_valid_stake(self, peer):

        if self.amt <= 0:
            return False
        
        if not self.is_valid_signature():
            return False

        if(self.amt > peer.chain.calc_balance(self.staker, peer.mem_pool)):
            return False

        return True