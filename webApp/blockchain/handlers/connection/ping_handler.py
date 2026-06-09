import uuid

from webApp.blockchain.handlers.base_handler import BaseHandler

class PingHandler(BaseHandler):

    async def handle(self, websocket, msg):

        print("Ping Handler\n")

        pkt = {
            "type": "pong",
            "id": str(uuid.uuid4())
        }

        await self.peer.network.send_message(
            websocket,
            pkt
        )