from webApp.blockchain.handlers.base_handler import BaseHandler

from webApp.blockchain.blockchain_structures.chain.pos.utils import (
    isvalidChain,
    weight_of_chain,
)

class PoSChainHandler(BaseHandler):

    async def handle(self, websocket, msg):
        print("Received a Chain")
        block_dict_list = msg.get("chain")
        if not block_dict_list:
            return
        
        block_list = []

        for block_dict in block_dict_list:
            block = self.peer.block_dict_to_block(block_dict)
            block_list.append(block)

        if not isvalidChain(block_list):
            print("\nInvalid Chain\n")
            return

        # If chain doesn't already exist we assign this as the chain
        if self.peer.chain.chain == []:
            self.peer.chain.rewrite(block_list)
            self.peer.save_chain_to_disk()
            
        else:
            pos = self.peer.chain.checkEquivalence(block_list)
            if pos != -1:
                block1 = self.peer.chain.chain[pos]
                block2 = block_list[pos]

                if block1.creator != block2.creator:  # Non malicious fork
                    l1 = len(self.peer.chain.chain)
                    l2 = len(block_list)
                    if l2 > l1:
                        self.peer.chain.rewrite(block_list)
                        self.peer.save_chain_to_disk()
                else:  # Malicious fork
                    await self.peer.verify_and_slash(block1, block2, pos, block_list)
                    
            elif weight_of_chain(self.peer.chain.chain) < weight_of_chain(block_list):
                self.peer.chain.rewrite(block_list)
                print("\nCurrent chain replaced by heavier chain\n")
                self.peer.save_chain_to_disk()
            
            else:
                print("\nCurrent Chain heavier than received chain\n")

        async with self.peer.mem_pool_condition:
            for transaction in self.peer.mem_pool:
                if self.peer.chain.transaction_exists_in_chain(transaction):
                    self.peer.mem_pool.remove(transaction)
        
        async with self.peer.ipfs.file_hashes_lock:
            for hash in list(self.peer.ipfs.file_hashes.keys()):
                if self.peer.chain.cid_exists_in_chain(hash):
                    self.peer.ipfs.file_hashes.pop(hash, None)
