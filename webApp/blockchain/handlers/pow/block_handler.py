import asyncio

from webApp.blockchain.handlers.base_handler import BaseHandler

class PoWBlockHandler(BaseHandler):

    async def handle(self, websocket, msg):
        new_block_dict=msg["block"]
        newBlock=self.peer.block_dict_to_block(new_block_dict)

        if not self.peer.chain.isValidBlock(newBlock):
            print("\nInvalid Block\n")
            return
        
        newBlock.miner=msg["miner"]
        self.peer.chain.chain.append(newBlock)
        print("\n\n Block Appended \n\n")

        for transaction in newBlock.transactions:
            if transaction.receiver == "deploy":
                contract_id = self.peer.contract.calculate_contract_id(transaction.sender, transaction.ts)
                code = transaction.payload[0]
                self.peer.contract.store_contract(contract_id, code)

        if self.peer.miner and self.peer.mine_task and not self.peer.mine_task.done():
            self.peer.mine_task.cancel()
            print("New Block received Cancelled Mining...")
        
        async with self.peer.mem_pool_condition:
            for transaction in self.peer.mem_pool:
                if newBlock.transaction_exists_in_block(transaction):
                    self.peer.mem_pool.remove(transaction)

        async with self.peer.ipfs.file_hashes_lock:
            for hash in list(self.peer.ipfs.file_hashes.keys()):
                if newBlock.cid_exists_in_block(hash):
                    self.peer.ipfs.file_hashes.pop(hash, None)
                    
        if self.peer.miner:
            self.peer.mine_task=asyncio.create_task(self.peer.mine_blocks())
        await self.peer.network.broadcast_message(msg)
        self.peer.save_chain_to_disk()
