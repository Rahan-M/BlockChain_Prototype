from webApp.blockchain.handlers.base_handler import BaseHandler

class MinersListHandler(BaseHandler):

    async def handle(self, websocket, msg):

        try:
            public_key = VerifyingKey.from_pem(self.peer.get_public_key_by_node_id(self.peer.admin_id).encode())
            message = json.dumps({
                "type":"miners_list_update",
                "id":msg["id"],
                "miners_list":msg["miners_list"],
                "activation_block":msg["activation_block"],
            }, sort_keys=True).encode()
            signature = binascii.unhexlify(msg["signature"])

            public_key.verify(signature, message)

        except Exception as e:
            print(f"Invalid miners list update signature: {e}")
            return
        
        self.peer.miners.append([msg["miners_list"], msg["activation_block"]])

        await self.peer.network.broadcast_message(msg)