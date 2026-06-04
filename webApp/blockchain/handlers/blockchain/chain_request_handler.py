import uuid

from webApp.blockchain.handlers.base_handler import BaseHandler

class ChainRequestHandler(BaseHandler):

    async def handle(self, websocket, msg):

        if not self.peer.chain:
            return

        pkt={
            "type" : "chain",
            "id" : str(uuid.uuid4()),
            "chain" : self.peer.chain.to_block_dict_list()
        }
        
        await self.peer.network.send_message(websocket, pkt)