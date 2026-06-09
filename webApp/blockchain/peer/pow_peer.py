import asyncio
import base64
import sys
import traceback
import uuid

import websockets

from webApp.blockchain.blockchain_structures.chain.pow.pow import Chain
from webApp.blockchain.blockchain_structures.block.pow.pow import Block
from webApp.blockchain.blockchain_structures.transaction import Transaction
from webApp.blockchain.peer.base_peer import BasePeer
from webApp.blockchain.blockchain_structures.utils import txs_to_json_digestable_form
from webApp.blockchain.utils import normalize_endpoint

class PoWPeer(BasePeer):

    def __init__(self, host, port, name, miner,
                 activate_disk_load=False,
                 activate_disk_save=False):

        self.consensus = "pow"

        super().__init__(
            "pow",
            host,
            port,
            name,
            activate_disk_load,
            activate_disk_save
        )

        # ---------------- CHAIN ----------------
        chain = None
        if self.storage.get_disk_load_status():
            chain = self.load_chain_from_disk()
        self.chain = Chain(chain)

        self.miner = miner

    # ---------------- RETRIEVAL METHODS ----------------

    def get_my_info(self):
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "account_balance": self.get_account_balance(),
            "public_key": self.wallet.public_key_pem,
            "private_key": self.wallet.private_key_pem,
            "node_id": self.node_id
        }

    def get_account_balance(self):
        return self.chain.calc_balance(self.wallet.public_key_pem, self.mem_pool)

    def get_chain(self):

        chain = self.chain.chain

        chain_list = []
        for block in chain:
            file_list = []
            for cid, desc in block.files.items():
                file_list.append({
                    "cid": cid,
                    "desc": desc,
                })
            chain_list.append({
                "id": block.id,
                "prevHash": block.prevHash,
                "transactions": txs_to_json_digestable_form(block.transactions),
                "ts": block.ts,
                "nonce": block.nonce,
                "hash": block.hash,
                "miner": block.miner,
                "files": file_list,
            })
        
        return chain_list

    # ---------------- CONVERTER METHODS ----------------

    def block_dict_to_block(self, block_dict):    
        """
            This function creates a block out of the information
            stored inside block_dict
            We sent a receive blocks as a dictionary
            block["trasnsactions"] is a list of dictionaries that
            represent transactions
        """

        new_block_id=block_dict["id"]
        new_block_prevHash=block_dict["prevHash"]
        new_block_ts=block_dict["ts"]
        new_block_nonce=block_dict["nonce"]

        transactions=[]
        for transaction_dict in block_dict["transactions"]:
            transaction=Transaction(transaction_dict["payload"], transaction_dict["sender"], transaction_dict["receiver"], transaction_dict["id"], transaction_dict["ts"])
            if(transaction.sender!="Genesis"):
                transaction.sign=base64.b64decode(transaction_dict["sign_b64"])
            transactions.append(transaction)

        
        newBlock=Block(new_block_prevHash, transactions, new_block_ts, new_block_nonce, new_block_id)   
        newBlock.files=block_dict["files"]

        return newBlock

    # ---------------- BLOCK ----------------

    async def create_blocks(self):
        """
            We mine blocks whenever there are greater than or equal to three
            transactions in mem pool
        """
        while True:
            await asyncio.sleep(30)
            async with self.mem_pool_condition:
                if(len(self.mem_pool)>0):
                    transaction_list=[]
                    for transaction in self.mem_pool:
                        if self.chain.transaction_exists_in_chain(transaction):
                            self.mem_pool.remove(transaction)
                            continue
                        else:
                            transaction_list.append(transaction)

                    if(len(transaction_list)>0):
                        newBlock=Block(self.chain.lastBlock.hash, transaction_list)
                        newBlock.files=self.ipfs.file_hashes.copy()

                        await asyncio.to_thread(self.chain.mine, newBlock)
                        newBlock.miner=self.wallet.public_key_pem

                        if self.chain.isValidBlock(newBlock):
                            self.chain.chain.append(newBlock)
                            print("\nBlock Appended \n")

                            for transaction in newBlock.transactions:
                                if transaction.receiver == "deploy":
                                    contract_id = self.contract.calculate_contract_id(transaction.sender, transaction.ts)
                                    code = transaction.payload[0]
                                    self.contract.store_contract(contract_id, code)
                            
                            async with self.ipfs.file_hashes_lock:
                                for hash in list(self.ipfs.file_hashes.keys()):
                                    if newBlock.cid_exists_in_block(hash):
                                        self.ipfs.file_hashes.pop(hash, None)

                            for transaction in self.mem_pool:
                                if newBlock.transaction_exists_in_block(transaction):
                                    self.mem_pool.remove(transaction)
                                        
                            pkt={
                                "type":"new_block",
                                "id":str(uuid.uuid4()),
                                "block":newBlock.to_dict(),
                                "miner":self.wallet.public_key_pem
                            }
                            await self.network.broadcast_message(pkt)
                            self.save_chain_to_disk()
                        else:
                            print("\n Invalid Block \n")

    # ---------------- WALLET ----------------

    async def send_money(self, amount, receiver_public_key):

        if(amount <= 0):
            print("Invalid Amount\n")
            return

        if(amount > self.chain.calc_balance(self.wallet.public_key_pem, self.mem_pool)):
            print("Not Enough Balance\n")
            return

        await self.create_and_broadcast_transaction(amount, receiver_public_key)

    # ---------------- SMART CONTRACT ----------------

    async def deploy_contract(self, contract_code):

        cost = self.contract.get_deploy_cost(contract_code)

        payload = [contract_code, cost]

        if(cost > self.chain.calc_balance(self.wallet.public_key_pem, self.mem_pool)):
            print("Not Enough Balance\n")
            return

        receiver_public_key = "deploy"

        await self.create_and_broadcast_transaction(payload, receiver_public_key)

    async def invoke_contract(self, contract_id, func_name, args):

        cost, new_state = self.contract.get_invoke_cost_and_new_state(contract_id, func_name, args)

        payload = [contract_id, func_name, args, new_state, cost]

        if(cost > self.chain.calc_balance(self.wallet.public_key_pem, self.mem_pool)):
            print("Not Enough Balance\n")
            return

        receiver_public_key = "invoke"

        await self.create_and_broadcast_transaction(payload, receiver_public_key)

    # ---------------- STARTUP & TERMINATION ----------------

    async def run_forever(self):
        # Start background tasks
        self.consensus_task = asyncio.create_task(self.find_longest_chain())
        self.disc_task = asyncio.create_task(self.network.discover_peers())
        self.sampler_task = asyncio.create_task(self.network.gossip_peer_sampler())
        if self.miner:
            self.mine_task = asyncio.create_task(self.create_blocks())

    async def start_blockchain(self):
        # adding node_id name mappings of admin
        self.name_to_node_id_dict[self.name.lower()] = self.node_id
        self.node_id_to_name_dict[self.node_id] = self.name.lower() 

        try:
            self.server = await websockets.serve(self.network.handle_connections, self.host, self.port)
            asyncio.create_task(self.server.wait_closed())
        except: # Catches all BaseException descendants
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(f"An unexpected error occurred!")
            print(f"Type: {exc_type.__name__}")
            print(f"Value: {exc_value}")
            print(f"Traceback object: {exc_traceback}")
            # You can also use traceback.print_exc() for a more standard traceback output
            import traceback
            traceback.print_exc()
        
        self.chain.create_genesis_block(self.wallet.public_key_pem)

        self.keepalive_task = asyncio.get_event_loop().create_task(
            self.run_forever()
        )

    async def connect_to_blockchain(self, bootstrap_host, bootstrap_port):
        # adding node_id name mappings of admin
        self.name_to_node_id_dict[self.name.lower()] = self.node_id
        self.node_id_to_name_dict[self.node_id] = self.name.lower()

        try:
            self.server = await websockets.serve(self.network.handle_connections, self.host, self.port)
            asyncio.create_task(self.server.wait_closed())
            normalized_bootstrap_host, normalized_bootstrap_port = normalize_endpoint((bootstrap_host, bootstrap_port))
            asyncio.create_task(self.network.connect_to_peer(normalized_bootstrap_host, normalized_bootstrap_port))
        except: # Catches all BaseException descendants
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(f"An unexpected error occurred!")
            print(f"Type: {exc_type.__name__}")
            print(f"Value: {exc_value}")
            print(f"Traceback object: {exc_traceback}")
            # You can also use traceback.print_exc() for a more standard traceback output
            traceback.print_exc()
        
        self.keepalive_task = asyncio.get_event_loop().create_task(
            self.run_forever()
        )

    async def stop(self):
        if self.disc_task:
            self.disc_task.cancel()
            print("Discover task cancelled")

        if self.consensus_task:
            self.consensus_task.cancel()

        if self.mine_task:
            self.mine_task.cancel()

        if self.sampler_task:
            self.sampler_task.cancel()
        
        if self.keepalive_task:
            self.keepalive_task.cancel()

        if self.ipfs.daemon_process:
            self.ipfs.stop_daemon()

        if self.server:
            print(f"\nServer : {self.server}\n")
            self.server.close()
            await self.server.wait_closed()
