from webApp.blockchain.handlers.base_handler import BaseHandler

class FileHandler(BaseHandler):

    async def handle(self, websocket, msg):

        cid=msg["cid"]
        desc=msg["desc"]

        async with self.peer.ipfs.file_hashes_lock:
            self.peer.ipfs.file_hashes[cid]=desc

        await self.peer.network.broadcast_message(msg)