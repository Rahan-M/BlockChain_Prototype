import ast
import json
import uuid
import asyncio

from pathlib import Path
from typing import List

from webApp.blockchain.storage.storage_manager import StorageManager
from webApp.blockchain.ipfs.ipfs_manager import IPFSManager
from webApp.blockchain.wallet.wallet_manager import WalletManager
from webApp.blockchain.network.network_manager import NetworkManager
from webApp.blockchain.network.message_router import MessageRouter
from webApp.blockchain.contract.contract_manager import ContractManager

from webApp.blockchain.blockchain_structures.transaction import Transaction

from webApp.blockchain.blockchain_structures.utils import txs_to_json_digestable_form

class BasePeer:

    def __init__(
        self,
        consensus_type: str,
        host: str,
        port: int,
        name: str,
        activate_disk_load: bool,
        activate_disk_save: bool,
    ):

        self.host = host
        self.port = port
        self.name = name.lower()

        # ---------------- PERSISTENT STORAGE ----------------

        self.storage = StorageManager(
            consensus_type,
            activate_disk_load,
            activate_disk_save
        )

        # ---------------- NODE ID ----------------

        node_id = None

        if self.storage.get_disk_load_status():
            node_id = self.load_node_id_from_disk()

        self.node_id = node_id or str(uuid.uuid4())

        self.save_node_id_to_disk()

        # ---------------- IPFS ----------------

        self.ipfs = IPFSManager(port)

        # ---------------- WALLET ----------------

        key = None

        if self.storage.get_disk_load_status():
            key = self.load_key_from_disk()

        self.wallet = WalletManager(self, key)

        self.save_key_to_disk()

        # ---------------- NETWORK ----------------

        known_peers = None

        if self.storage.get_disk_load_status():
            known_peers = self.load_known_peers_from_disk()

        self.network = NetworkManager(self, known_peers)

        # ---------------- MESSAGE ROUTER ----------------

        self.router = MessageRouter(self)

        # ---------------- SMART CONTRACT ----------------

        self.contract = ContractManager(self)

        # ---------------- SHARED STATE ----------------

        self.seen_message_ids = set()

        self.mem_pool = []

        self.mem_pool_condition = asyncio.Condition()

        # ---------------- COMMON REGISTRIES ----------------

        self.name_to_public_key_dict = {}

        self.node_id_to_name_dict = {}

        self.name_to_node_id_dict = {}

        # ---------------- COMMON TASKS ----------------

        self.mine_task = None
        self.disc_task = None
        self.consensus_task = None
        self.sampler_task = None
        self.server = None
        self.outgoing_conn_task = None
        self.keepalive_task = None

    # ---------------- RETRIEVAL METHODS ----------------

    def get_known_peers(self):
        
        known_peers=[{"host":h, "port":p, "name":n, "public_key":s, "node_id":i}
               for (h, p), (n, s, i) in self.network.known_peers.items()]

        return known_peers

    def get_pending_transactions(self):

        return txs_to_json_digestable_form(self.mem_pool)

    def get_files(self):
        pass

    def get_contracts(self):
        contracts = []
        for contract_id in self.contract.contracts:
            contracts.append({
                "id": contract_id,
                "code": self.contract.contracts[contract_id],
            })
        return contracts

    def get_contracts_state(self):

        states = []
        for contract_id in self.contract.contracts:
            states.append({
                "id": contract_id,
                "state": self.contract.get_contract_state(contract_id),
            })

        return states

    # ---------------- PERSISTENT STORAGE ----------------

    def load_node_id_from_disk(self):
        return self.storage.load_node_id()
    
    def save_node_id_to_disk(self):
        if not self.storage.get_disk_save_status():
            return
        node_id = self.node_id
        self.storage.save_node_id(node_id)

    def load_key_from_disk(self):
        return self.storage.load_key()

    def save_key_to_disk(self):
        if not self.storage.get_disk_save_status():
            return
        key = self.wallet.private_key_pem
        self.storage.save_key(key)

    def load_chain_from_disk(self):
        block_dict_list = self.storage.load_chain()
        if not block_dict_list:
            return None
        
        block_list = []
        for block_dict in block_dict_list:
            block=self.block_dict_to_block(block_dict)
            block_list.append(block)
        return block_list

    def save_chain_to_disk(self):
        if not self.storage.get_disk_save_status():
            return
        chain = self.chain.to_block_dict_list()
        self.storage.save_chain(chain)

    def load_known_peers_from_disk(self):
        content = self.storage.load_peers()
        if not content:
            return None
        known_peers = {}
        for key, value in content.items():
            known_peers[tuple(ast.literal_eval(key))] = tuple(value)
        for key, value in known_peers.items():
            self.name_to_public_key_dict[value[0].lower()] = value[1]
            self.node_id_to_name_dict[value[2]] = value[0].lower()
            self.name_to_node_id_dict[value[0].lower()] = value[2]
        return known_peers

    def save_known_peers_to_disk(self):
        if not self.storage.get_disk_save_status():
            return
        content = {}
        for key, value in self.network.known_peers.items():
            content[json.dumps(key)] = list(value)
        self.storage.save_peers(content)

    # ---------------- TRANSACTION ----------------

    async def add_transaction_to_mempool(self, transaction):

        async with self.mem_pool_condition:
            self.mem_pool.append(transaction)

    async def create_and_broadcast_transaction(self, payload, receiver_public_key):

        transaction = Transaction(payload, self.wallet.public_key_pem, receiver_public_key)
        
        transaction.sign_transaction(self.wallet.private_key)

        transaction_str = transaction.to_string(include_signature=True)

        await self.add_transaction_to_mempool(transaction)
        
        print("Transaction Created", transaction)
        print("\n")

        await self.network.broadcast_transaction(transaction_str)

    # ---------------- BLOCK ----------------

    async def create_blocks(self):
        pass

    # ---------------- IPFS ----------------

    async def upload_file(self, desc: str, path:str):
        file_path=Path(path)
        if(not file_path.is_file()):
            print("\nFile doesn't exist\n")
            return

        if not self.ipfs.daemon_process:
            self.ipfs.start_daemon()
        
        cid, name = await asyncio.to_thread(self.ipfs.add_to_ipfs, path)
        if(not(cid and name)):
            return
        
        print(f"\nNew File Created : {cid}\n")
        pkt={
            "type":"file",
            "id":str(uuid.uuid4()),
            "desc":desc,
            "cid":cid
        }
        
        self.seen_message_ids.add(pkt["id"])
        async with self.ipfs.file_hashes_lock:
            self.ipfs.file_hashes[cid]=desc
        return pkt

    async def download_file(self, cid, path):
        
        self.ipfs.download_ipfs_file_subprocess(cid, path)

    # ---------------- CHAIN CONSENSUS ----------------

    async def find_longest_chain(self):
        """
            We routinely check every 30 seconds, every other chain and we replace
            ours with theirs if theirs is >= ours
        """
        while True:
            pkt={
                "type":"chain_request",
                "id":str(uuid.uuid4())
            }
            await self.network.broadcast_message(pkt)
            print("\nSent out chain requests...")
            for _ in range(12):
                    await asyncio.sleep(5)
