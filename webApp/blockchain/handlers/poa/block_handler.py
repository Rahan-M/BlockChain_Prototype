import asyncio

from webApp.blockchain.handlers.base_handler import BaseHandler

class PoABlockHandler(BaseHandler):

    async def handle(self, websocket, msg):
        new_block_dict=msg["block"]
        newBlock=self.peer.block_dict_to_block(new_block_dict)
        miners_list = self.peer.get_current_miners_list()
        reqd_miner_node_id = miners_list[(len(self.peer.chain.chain) + self.peer.round) % len(miners_list)]
        reqd_miner_public_key = self.peer.get_public_key_by_node_id(reqd_miner_node_id)

        if not self.peer.chain.isValidBlock(newBlock, reqd_miner_node_id, reqd_miner_public_key):
            print("\nInvalid Block\n")
            return
                
        self.peer.chain.chain.append(newBlock)
        print("\n\n Block Appended \n\n")

        for transaction in newBlock.transactions:
            if transaction.receiver == "deploy":
                contract_id = self.peer.contract.calculate_contract_id(transaction.sender, transaction.ts)
                code = transaction.payload[0]
                self.peer.contract.store_contract(contract_id, code)
        
        async with self.peer.mem_pool_condition:
            for transaction in self.peer.mem_pool:
                if newBlock.transaction_exists_in_block(transaction):
                    self.peer.mem_pool.remove(transaction)
                    
        async with self.peer.ipfs.file_hashes_lock:
            for hash in list(self.peer.ipfs.file_hashes.keys()):
                if newBlock.cid_exists_in_block(hash):
                    self.peer.ipfs.file_hashes.pop(hash, None)

        await self.peer.network.broadcast_message(msg)
        self.peer.round_task.cancel()
        try:
            await self.peer.round_task
        except asyncio.CancelledError:
            pass
        self.peer.round_task = asyncio.create_task(self.peer.round_calculator())

        while self.peer.miners:
            if self.peer.miners[0][1] < len(self.peer.chain.chain):
                self.peer.miners.pop(0)
            else:
                break

        new_miners_list = self.peer.get_current_miners_list()
        if self.peer.node_id in new_miners_list:
            await self.peer.update_role(True)
        else:
            await self.peer.update_role(False)
        self.peer.save_chain_to_disk()