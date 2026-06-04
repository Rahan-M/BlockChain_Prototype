import uuid

from webApp.blockchain.handlers.base_handler import BaseHandler

class NetworkDetailsHandler(BaseHandler):

    async def handle(self, websocket, msg):

        self.peer.admin_id = msg["admin"]
        self.peer.miners = msg["miners"]

        pkt={
            "type": "chain_request",
            "id": str(uuid.uuid4())
        }
        await self.peer.network.send_message(websocket, pkt)
