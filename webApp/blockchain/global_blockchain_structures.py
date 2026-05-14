import json, uuid, base64
from typing import List
from datetime import datetime
from ecdsa import VerifyingKey, SigningKey, SECP256k1

class Transaction:
    def __init__(self, payload, sender: str, receiver: str, id=None, ts=None):
        self.id=id or str(uuid.uuid4())
        self.payload=payload   # amount or [code, amount] or [contract id, function_name, arguments, state, amount]
        self.sender: str=sender  # Public Key
        self.receiver: str=receiver   # Public Key or "deploy" or "invoke"
        self.sign:bytes=None
        self.ts=ts or datetime.now().timestamp()

    def to_dict(self):
        dict={
            "id":self.id,
            "payload":self.payload,
            "sender":self.sender,
            "receiver":self.receiver,
            "ts":self.ts
        }
        return dict
    
    def __eq__(self, other):
        return(
            self.id==other.id and
            self.sender==other.sender and
            self.receiver==other.receiver and
            self.ts==other.ts
        )
    
    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return json.dumps(self.to_dict())
    
    def is_valid_signature(self):
        try:
            # Load public key from PEM string
            public_key = VerifyingKey.from_pem(self.sender.encode())

            message = str(self).encode()

            public_key.verify(self.sign, message)
            return True
        except Exception as e:
            print(f"Invalid transaction signature: {e}")
            return False
    
def txs_to_json_digestable_form(transactions: List[Transaction]):
    l=[]
    for i in range(len(transactions)):
        tx_dict=transactions[i].to_dict()
        if(transactions[i].sender!="Genesis"):
            tx_dict["sign"]=base64.b64encode(transactions[i].sign).decode()
        l.append(tx_dict)
    return l


class Wallet:
    def __init__(self, private_key_pem: str = None):
        if not private_key_pem:
            self.private_key = SigningKey.generate(curve=SECP256k1)
        else:
            self.private_key = SigningKey.from_pem(private_key_pem)
            
        self.private_key_pem = self.private_key.to_pem().decode()

        self.public_key = self.private_key.get_verifying_key()

        self.public_key_pem = self.public_key.to_pem().decode()