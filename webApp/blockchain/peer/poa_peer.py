import asyncio
import base64
import json
import sys
import traceback
import uuid

import websockets

from webApp.blockchain.blockchain_structures.transaction import Transaction
from webApp.blockchain.blockchain_structures.block.poa.poa import Block
from webApp.blockchain.blockchain_structures.chain.poa.poa import Chain
from webApp.blockchain.peer.base_peer import BasePeer

from webApp.blockchain.blockchain_structures.utils import txs_to_json_digestable_form
from webApp.blockchain.utils import normalize_endpoint

class PoAPeer(BasePeer):

    def __init__(self, host, port, name,
                 activate_disk_load=False,
                 activate_disk_save=False):

        self.consensus = "poa"

        super().__init__(
            "poa",
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

        self.miner = False

        self.round = 0

        self.admin_id = None

        self.miners = []

        self.round_task = None

    # ---------------- RETRIEVAL METHODS ----------------

    def get_my_info(self):
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "account_balance": self.get_account_balance(),
            "public_key": self.wallet.public_key_pem,
            "private_key": self.wallet.private_key_pem,
            "node_id": self.node_id,
            "admin_id": self.admin_id
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
                "hash": block.hash,
                "miner_node_id": block.miner_node_id,
                "miner_public_key":  block.miner_public_key,
                "miners_list": block.miners_list,
                "files": file_list,
            })

        return chain_list

    def get_current_miners_list(self):
        miners_list = None
        if self.miners and len(self.chain.chain) == self.miners[0][1]:
            miners_list = self.miners[0][0]
            for i in range(1, len(self.miners)):
                if self.miners[i][1] == len(self.chain.chain):
                    miners_list = self.miners[i][0]
                else:
                    break
        else:
            miners_list = self.chain.chain[-1].miners_list
        return miners_list

    # ---------------- CONVERTER METHODS ----------------

    def block_dict_to_block(self, block_dict):

        new_block_id=block_dict["id"]
        new_block_prevHash=block_dict["prevHash"]
        new_block_ts=block_dict["ts"]
        new_block_miner_node_id = block_dict["miner_node_id"]
        new_block_miner_public_key = block_dict["miner_public_key"]
        new_block_miners_list = block_dict["miners_list"]
        new_block_signature = block_dict["signature"]

        transactions=[]
        for transaction_dict in block_dict["transactions"]:
            transaction=Transaction(transaction_dict["payload"], transaction_dict["sender"], transaction_dict["receiver"], transaction_dict["id"], transaction_dict["ts"])
            if(transaction.sender!="Genesis"):
                transaction.sign=base64.b64decode(transaction_dict["sign_b64"])
            transactions.append(transaction)
        
        newBlock=Block(new_block_prevHash, transactions, new_block_ts, new_block_id)
        newBlock.miner_node_id = new_block_miner_node_id
        newBlock.miner_public_key = new_block_miner_public_key
        newBlock.miners_list = new_block_miners_list
        newBlock.files=block_dict["files"]
        newBlock.signature = new_block_signature
        return newBlock

    async def broadcast_miners_list(self, miners_list, activation_block):
        pkt={
            "type":"miners_list_update",
            "id":str(uuid.uuid4()),
            "miners_list": miners_list,
            "activation_block": activation_block,
        }
        message = json.dumps(pkt, sort_keys=True).encode()
        signature = self.wallet.private_key.sign(message)
        pkt["signature"] = signature.hex()
        await self.network.broadcast_message(pkt)

    # ---------------- HELPER METHODS ----------------

    def get_public_key_by_node_id(self, target_node_id):
        for (host, port), (name, public_key, node_id) in self.network.known_peers.items():
            if node_id == target_node_id:
                return public_key
        return None

    def is_found_node_id(self, target_node_id):
        for (host, port), (name, public_key, node_id) in self.network.known_peers.items():
            if node_id == target_node_id:
                return True
        return False

    async def round_calculator(self):
        self.round = 0
        try:
            while True:
                for _ in range(2):
                    await asyncio.sleep(5)
                if len(self.mem_pool) > 0:
                    for _ in range(16):
                        await asyncio.sleep(5)
                    print("Shifting miner...")
                    self.round = self.round + 1
                    print("Miner shifted")
        except asyncio.CancelledError:
            print("Round calculator task stopped cleanly")

    async def update_role(self, is_miner_now): 
        if is_miner_now and not self.miner:
            # Become miner
            self.miner = True
            self.mine_task = asyncio.create_task(self.create_blocks())

        elif not is_miner_now and self.miner:
            # Stop mining
            self.miner = False
            if self.mine_task:
                try:
                    self.mine_task.cancel()
                    await self.mine_task
                except asyncio.CancelledError:
                    pass

    # ---------------- BLOCK ----------------

    def sign_block(self, block: Block):
        message = block.get_message_to_sign()
        signature = self.wallet.private_key.sign(message)
        block.signature = signature.hex()  # Store as hex string for transport

    async def create_blocks(self):
        try:
            while True:
                for _ in range(6):
                    await asyncio.sleep(5)
                miners_list = self.get_current_miners_list()
                reqd_miner_node_id = miners_list[(len(self.chain.chain) + self.round) % len(miners_list)]
                if self.node_id == reqd_miner_node_id:
                    if self.round != 0:
                        for _ in range(3):
                            await asyncio.sleep(5)
                    async with self.mem_pool_condition: # Works the same as lock
                        if(len(self.mem_pool)>0):
                            transaction_list=[]
                            for transaction in self.mem_pool:
                                if self.chain.transaction_exists_in_chain(transaction):
                                    self.mem_pool.remove(transaction)
                                    continue
                                else:
                                    transaction_list.append(transaction)

                            if(len(transaction_list)>0):
                                print("Mining Started")
                                print("Mining...")
                                newBlock = Block(self.chain.lastBlock.hash, transaction_list)
                                newBlock.miner_node_id = self.node_id
                                newBlock.miner_public_key = self.wallet.public_key_pem
                                newBlock.miners_list = miners_list
                                newBlock.files=self.ipfs.file_hashes.copy()
                                self.sign_block(newBlock)

                                reqd_miner_pulic_key = self.wallet.public_key_pem
                                if not self.chain.isValidBlock(newBlock, reqd_miner_node_id, reqd_miner_pulic_key):
                                    print("\nInvalid Block\n")
                                    return
                        
                                self.chain.chain.append(newBlock)
                                print("\nBlock Appended \n")

                                for transaction in newBlock.transactions:
                                    if transaction.receiver == "deploy":
                                        contract_id = self.contract.calculate_contract_id(transaction.sender, transaction.ts)
                                        code = transaction.payload[0]
                                        self.contract.store_contract(contract_id, code)

                                for transaction in self.mem_pool:
                                    if newBlock.transaction_exists_in_block(transaction):
                                        self.mem_pool.remove(transaction)

                                async with self.ipfs.file_hashes_lock:
                                    for hash in list(self.ipfs.file_hashes.keys()):
                                        if newBlock.cid_exists_in_block(hash):
                                            self.ipfs.file_hashes.pop(hash, None)

                                pkt={
                                    "type":"new_block",
                                    "id":str(uuid.uuid4()),
                                    "block":newBlock.to_dict()
                                }

                                await self.network.broadcast_message(pkt)
                                self.round_task.cancel()
                                await self.round_task
                                self.round_task = asyncio.create_task(self.round_calculator())

                                while self.miners:
                                    if self.miners[0][1] < len(self.chain.chain):
                                        self.miners.pop(0)
                                    else:
                                        break

                                new_miners_list = self.get_current_miners_list()
                                if self.node_id in new_miners_list:
                                    await self.update_role(True)
                                else:
                                    await self.update_role(False)
                                self.save_chain_to_disk()

        except asyncio.CancelledError:
            print("Miner task stopped cleanly")
            raise

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
        self.consensus_task = asyncio.create_task(self.find_longest_chain())
        self.disc_task = asyncio.create_task(self.network.discover_peers())
        self.sampler_task = asyncio.create_task(self.network.gossip_peer_sampler())
        self.round_task = asyncio.create_task(self.round_calculator())

    async def start_blockchain(self):
        # adding node_id name mappings of admin
        self.name_to_node_id_dict[self.name.lower()] = self.node_id
        self.node_id_to_name_dict[self.node_id] = self.name.lower()

        # setup listening server
        try:
            self.server = await websockets.serve(self.network.handle_connections, self.host, self.port)
            asyncio.create_task(self.server.wait_closed())
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(f"An unexpected error occurred!")
            print(f"Type: {exc_type.__name__}")
            print(f"Value: {exc_value}")
            print(f"Traceback object: {exc_traceback}")
            import traceback
            traceback.print_exc()
        
        # add genesis block
        self.chain.add_genesis_block(self.wallet.public_key_pem)

        # set genesis block fields
        self.chain.chain[0].miner_node_id = self.node_id
        self.chain.chain[0].miner_public_key = self.wallet.public_key_pem
        self.chain.chain[0].miners_list = [self.node_id]
        self.sign_block(self.chain.chain[0])

        # setting blockchain creator as admin
        self.admin_id = self.node_id

        # start miner
        await self.update_role(True)

        # start background tasks
        self.keepalive_task = asyncio.get_event_loop().create_task(
            self.run_forever()
        )

    async def connect_to_blockchain(self, bootstrap_host, bootstrap_port):
        # adding node_id name mappings of admin
        self.name_to_node_id_dict[self.name.lower()] = self.node_id
        self.node_id_to_name_dict[self.node_id] = self.name.lower()
        
        # setup listening server and connect to a peer
        try:
            self.server=await websockets.serve(self.network.handle_connections, self.host, self.port)
            asyncio.create_task(self.server.wait_closed())
            normalized_bootstrap_host, normalized_bootstrap_port = normalize_endpoint((bootstrap_host, bootstrap_port))
            asyncio.create_task(
                self.network.connect_to_peer(
                    normalized_bootstrap_host,
                    normalized_bootstrap_port
                )
            )
        except:
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(f"An unexpected error occurred!")
            print(f"Type: {exc_type.__name__}")
            print(f"Value: {exc_value}")
            print(f"Traceback object: {exc_traceback}")
            traceback.print_exc()
        
        # start background tasks
        self.keepalive_task = asyncio.get_event_loop().create_task(
            self.run_forever()
        )

    async def stop(self):
        if self.disc_task:
            self.disc_task.cancel()
            print("Discover task cancelled")

        if self.consensus_task:
            self.consensus_task.cancel()

        if self.sampler_task:
            self.sampler_task.cancel()

        if self.round_task:
            self.round_task.cancel()

        if self.keepalive_task:
            self.keepalive_task.cancel()

        if self.ipfs.daemon_process:
            self.ipfs.stop_daemon()

        if self.server:
            print(f"\nServer : {self.server}\n")
            self.server.close()
            await self.server.wait_closed()

        await self.update_role(False)