import uuid
import json
import base64

from datetime import datetime

from ecdsa import VerifyingKey

class Transaction:
    def __init__(self, payload, sender: str, receiver: str, id = None, ts = None, sign = None):
        self.id = id or str(uuid.uuid4())
        self.payload = payload   # amount or [code, amount] or [contract id, function_name, arguments, state, amount]
        self.sender: str = sender  # Public Key
        self.receiver: str = receiver   # Public Key or "deploy" or "invoke"
        self.ts = ts or datetime.now().timestamp()
        self.sign:bytes = sign

    def __eq__(self, other):
        return(
            self.id==other.id and
            self.sender==other.sender and
            self.receiver==other.receiver and
            self.ts==other.ts
        )

    def to_dict(self, include_signature):
        data = {
            "id": self.id,
            "payload": self.payload,
            "sender": self.sender,
            "receiver": self.receiver,
            "ts": self.ts
        }

        if include_signature:
            data["sign"] = self.sign

        return data

    def to_string(self, include_signature):
        data = self.to_dict(include_signature)

        if include_signature and data["sign"] is not None:
            data["sign_b64"] = base64.b64encode(data.pop("sign")).decode()

        return json.dumps(data, sort_keys=True)

    def sign_transaction(self, private_key):

        include_signature = False
        transaction_str = self.to_string(include_signature)

        signature = private_key.sign(transaction_str.encode())

        self.sign = signature
    
    def __hash__(self):
        return hash(self.id)

    def is_valid_signature(self):

        try:
            public_key = VerifyingKey.from_pem(self.sender.encode())
            include_signature = False
            message = self.to_string(include_signature).encode()

            public_key.verify(self.sign, message)
            return True

        except Exception as e:
            print(f"Invalid transaction signature: {e}")
            return False

    def is_valid_deploy_payload(self, peer):
        
        contract_code = self.payload[0]
        cost = peer.contract.get_deploy_cost(contract_code)

        if(cost != self.payload[-1]):
            print("Wrong Deploy Cost\n")
            return False

        return True

    def is_valid_invoke_payload(self, peer):
        
        contract_id, func_name, args = self.payload[0], self.payload[1], self.payload[2]

        cost, new_state = peer.contract.get_invoke_cost_and_new_state(contract_id, func_name, args)

        if new_state != self.payload[3]:
            print("Wrong Invoke State\n")
            return False

        if cost != self.payload[-1]:
            print("Wrong Invoke Cost\n")
            return False

        return True

    def is_valid_transaction_payload(self, peer):

        amount = 0

        if self.receiver == "deploy":
            if not self.is_valid_deploy_payload(peer):
                return False
            amount = self.payload[-1]

        elif self.receiver == "invoke":
            if not self.is_valid_invoke_payload(peer):
                return False
            amount = self.payload[-1]

        else:
            amount = self.payload

        if(amount <= 0):
            print("\nInvalid Transaction Amount\n")
            return False

        bal = peer.chain.calc_balance(self.sender, peer.mem_pool)
        if(amount > bal):
            print("\nNot Enough Balance\n")
            return False

        return True

    def is_valid_transaction(self, peer):
        
        if not self.is_valid_signature():
            print("Invalid Signature\n")
            return False

        if not self.is_valid_transaction_payload(peer):
            print("Invalid Payload\n")
            return False

        return True
