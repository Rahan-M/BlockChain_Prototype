import json
import base64

from webApp.blockchain.blockchain_structures.transaction import Transaction

from webApp.blockchain.handlers.base_handler import BaseHandler

class TransactionHandler(BaseHandler):

    async def handle(self, websocket, msg):

        tx_str=msg["transaction"]
        try:
            tx = json.loads(tx_str)
        except json.JSONDecodeError:
            print("Invalid transaction JSON")
            return

        try:
            sign = base64.b64decode(msg["sign_b64"])
        except Exception:
            print("Invalid signature encoding")
            return
        
        transaction: Transaction=Transaction(tx['payload'], tx['sender'], tx['receiver'], tx['id'], tx['ts'], sign)
        
        if not transaction.is_valid_transaction(self.peer):
            print("\nInvalid Transaction\n")
            return

        if self.peer.chain.transaction_exists_in_chain(transaction):
            print(f"Transaction already exists in chain")
            return
        
        print("\nValid Transaction")
        print(f"\n{msg['type']}: {msg['transaction']}")
        print("\n")

        self.peer.add_transaction_to_mempool(transaction)

        await self.peer.network.broadcast_message(msg)