import asyncio
import base64
import hashlib
import sys
import traceback
import uuid

from datetime import datetime, timedelta
from typing import Any, Dict, List

import websockets

from webApp.blockchain.peer.base_peer import BasePeer
from webApp.blockchain.blockchain_structures.chain.pos.pos import Chain
from webApp.blockchain.blockchain_structures.block.pos.pos import Block
from webApp.blockchain.blockchain_structures.transaction import Transaction
from webApp.blockchain.blockchain_structures.pos.stake import Stake

from ecdsa import VerifyingKey, BadSignatureError

from webApp.blockchain.blockchain_structures.utils import txs_to_json_digestable_form
from webApp.blockchain.utils import normalize_endpoint

MAX_OUTPUT=2**256
EPOCH_TIME=60

class PoSPeer(BasePeer):

    def __init__(self, host, port, name, staker,
                 activate_disk_load=False,
                 activate_disk_save=False):

        self.consensus = "pos"

        super().__init__(
            "pos",
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

        self.staker = staker

        self.staked_amt = 0

        self.last_epoch_end_ts = datetime.now()

        self.current_stakes = set()

        self.current_stakers = {}

        self.curr_stakers_condition = asyncio.Condition()

        self.create_block_condition = asyncio.Condition()

        self.reset_task = None

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
            "tsle": (datetime.now() - self.last_epoch_end_ts).seconds
        }

    def get_account_balance(self):
        return self.chain.calc_balance(self.wallet.public_key_pem, self.mem_pool, self.current_stakers)

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

            stakes_dict_list:List[Dict]=[]
            for stake in block.stakers:
                include_signature = True
                stake_dict=stake.to_dict(include_signature)
                if(stake.sign):
                    stake_dict["sign"]=base64.b64encode(stake.sign).decode()
                stakes_dict_list.append(stake_dict)
            
            if(block.transactions[0].sender=="Genesis"):
                chain_list.append({
                    "id": block.id,
                    "prevHash": block.prevHash,
                    "transactions": txs_to_json_digestable_form(block.transactions),
                    "ts": block.ts,
                    "hash": block.hash,
                    "miner": block.creator,
                    "staked_amt":block.staked_amt,
                    "files": file_list,
                })
            else:
                chain_list.append({
                    "id": block.id,
                    "prevHash": block.prevHash,
                    "transactions": txs_to_json_digestable_form(block.transactions),
                    "ts": block.ts,
                    "hash": block.hash,
                    "miner": block.creator,
                    "staked_amt":block.staked_amt,
                    "files": file_list,
                    "stakes":stakes_dict_list,
                    "vrf_proof":base64.b64encode(block.vrf_proof).decode(),
                    "seed":block.seed
                })

        return chain_list

    # ---------------- CONVERTER METHODS ----------------

    def block_dict_to_block(self, block_dict:Dict[str, Any]):    
        """
            Verified whether given information in block_dict is valid and
            creates a block out of the information or returns None
            We sent a receive blocks as a dictionary
            block["trasnsactions"] is a list of dictionaries that
            represent transactions
        """

        new_block_id=block_dict.get("id")
        new_block_prevHash=block_dict.get("prevHash")
        new_block_ts=block_dict.get("ts")

        transactions=[]
        for transaction_dict in block_dict["transactions"]:
            transaction=Transaction(transaction_dict["payload"], transaction_dict["sender"], transaction_dict["receiver"], transaction_dict["id"], transaction_dict["ts"])
            if(transaction.sender!="Genesis"):
                transaction.sign=base64.b64decode(transaction_dict["sign_b64"])
            transactions.append(transaction)
        
        if(not(new_block_id and new_block_ts and transactions)): # Genesis block doesn't have prevHash, it's an empty string
            return None
        
        newBlock=Block(new_block_prevHash, transactions, new_block_ts, new_block_id)   
        staked_amt=block_dict.get("staked_amt")
        if(staked_amt):
            newBlock.staked_amt=staked_amt

        if(block_dict.get("files")):
            newBlock.files=block_dict["files"]

        creator=block_dict.get("creator")
        if(creator):
            newBlock.creator=creator

        sign_b64=block_dict.get("sign")

        if(sign_b64):
            newBlock.sign=base64.b64decode(sign_b64)

        stakers_list:List[Stake]=[]
        for staker_dict in block_dict["stakers"]:
            new_Stake=self.stake_dict_to_stake(staker_dict)
            if(not new_Stake):
                continue
            stakers_list.append(new_Stake)
        
        vrf_proof=block_dict.get("vrf_proof_b64")
        seed=block_dict.get("seed")
        if(vrf_proof and seed):
            newBlock.vrf_proof=base64.b64decode(vrf_proof)
            newBlock.seed=seed

        newBlock.stakers=stakers_list
        return newBlock

    def stake_dict_to_stake(self, stake_dict:Dict[str, Any]):    
        """
            This function creates a stake out of the information
            stored inside stake_dict
        """
        id=stake_dict.get("id")
        staker=stake_dict.get("staker")
        amt=stake_dict.get("amt")
        ts=stake_dict.get("ts")
        sign=stake_dict.get("sign_b64")

        if(not(id and staker and amt and sign)):
            return None
        
        stake=Stake(staker, amt, id, ts)

        sign_bytes=base64.b64decode(sign)        
        stake.sign=sign_bytes
        return stake

    async def verify_and_slash(self, block1:Block, block2:Block, pos:int, block_list:List[Block]):
        vk=VerifyingKey.from_pem(block1.creator)
        sign1=block1.sign
        sign2=block2.sign
        err1, err2=False, False

        try:
            vk.verify(sign1, str(block1).encode())
        except BadSignatureError:
            print("\nBad signature on block 1\n")
            err1=True
        try:
            vk.verify(sign2, str(block2).encode())
        except BadSignatureError:
            print("\nBad signature on block 2\n")
            err2=True
        

        if(err1 and not err2): # Unlikely since I'm checking blocks as they arrive
            self.chain.rewrite(block_list)
            return
        
        elif err2 and not err1: # Fault with arrived chain
            return
        
        self.chain.chain[pos].is_valid=False
        self.chain.chain[pos].slash_creator=True
        
        pkt={
            "type":"slash_announcement",
            "id":str(uuid.uuid4()),
            "evidence1":block1.to_dict_with_stakers(),
            "evidence2":block2.to_dict_with_stakers(),
            "block1_sign":base64.b64encode(block1.sign).decode(),
            "block2_sign":base64.b64encode(block2.sign).decode(),
            "pos":pos
        }
        await self.network.broadcast_message(pkt)
        # Now the receiver should make sure that the block1 creator signed both the blocks and it is he that is penalized in slash_block, also check my signature 
        # Then if Chain.instance.chain[pos]==block1 or block2 then make that block invalid and slash the creator

    async def send_stake_announcements(self, amt: float):

        new_stake = Stake(self.wallet.public_key_pem, amt)

        new_stake.sign_stake(self.wallet.private_key)
        
        include_signature = True
        pkt={
            "id": str(uuid.uuid4()),
            "type": "stake_announcement",
            "stake": new_stake.to_dict(include_signature)
        }

        async with self.curr_stakers_condition:
            self.current_stakers[self.wallet.public_key_pem] = amt
            self.current_stakes.add(new_stake)
        self.staked_amt = amt
        print("Stake Created")

        await self.network.broadcast_message(pkt)

    async def restart_epoch(self):
        while True:
            await asyncio.sleep(EPOCH_TIME/2)
            currTime=datetime.now()
            if(currTime-self.last_epoch_end_ts>timedelta(seconds=EPOCH_TIME*7/6)):
                self.last_epoch_end_ts=datetime.now()
                self.staked_amt=0
                self.current_stakers.clear()
                self.current_stakes.clear()

    # ---------------- BLOCK ----------------

    async def create_blocks(self, time):
        if(not self.staker):
            print(self.staker)
            return
    
        await asyncio.sleep(time)
        if(len(self.current_stakers)<=0):
            print("\nNo stakers\n")
            self.last_epoch_end_ts=datetime.now()
            self.staked_amt=0
            return
        
        transactions_in_mem_pool=self.mem_pool
        pending_transactions=[]
        for transaction in transactions_in_mem_pool:
            if(not self.chain.transaction_exists_in_chain(transaction)):
                pending_transactions.append(transaction)
        
        if(len(pending_transactions)<=0):
            print("\nNo pending transactions\n")
            self.last_epoch_end_ts=datetime.now()
            self.staked_amt=0
            async with self.curr_stakers_condition:
                self.current_stakers.clear()
                self.current_stakes.clear()
            return
        
        print("\nRunning vrf\n")
        async with self.curr_stakers_condition:# So that no new stakes don't comes in
            seed=self,chain.epoch_seed()
            vrf_proof=self.wallet.private_key.sign(seed.encode())
            vrf_output=hashlib.sha256(vrf_proof).hexdigest()
            vrf_output_int=int(vrf_output, 16)
            total_stake=sum(self.current_stakers.values())


            threshold=(self.staked_amt/total_stake)*MAX_OUTPUT
            if(vrf_output_int>=threshold):
                print("\nYou've lost\n")
                self.staked_amt=0
                return
            
            #The following code is for the winner
            print("\nYou won\n")
            newBlock=Block(self.chain.lastBlock.hash, pending_transactions)
            newBlock.files=self.ipfs.file_hashes.copy()
            newBlock.seed=seed
            newBlock.vrf_proof=vrf_proof
            self.chain.chain.append(newBlock)
            newBlock.staked_amt=self.staked_amt
            newBlock.creator=self.wallet.public_key_pem
            newBlock.stakers=self.current_stakers
            

            self.last_epoch_end_ts=datetime.now()
            print("Block Appended")

            for transaction in newBlock.transactions:
                if transaction.receiver == "deploy":
                    contract_id = self.contract.calculate_contract_id(transaction.sender, transaction.ts)
                    code = transaction.payload[0]
                    self.contract.store_contract(contract_id, code)

            newBlock.stakers=list(self.current_stakes)

            self.staked_amt=0
            self.current_stakers.clear()
            self.current_stakes.clear()

            sign=self.wallet.private_key.sign(str(newBlock).encode())
            newBlock.sign=sign

            vrf_proof_b64=base64.b64encode(vrf_proof).decode()
            sign_b64=base64.b64encode(sign).decode()

            print(f"\n{newBlock.to_dict_with_stakers()}\n")
            pkt={
                "type":"new_block",
                "id":str(uuid.uuid4()),
                "block":newBlock.to_dict_with_stakers(),
                "vrf_proof":vrf_proof_b64,
                "sign":sign_b64,
            }

            await self.network.broadcast_message(pkt)
            self.save_chain_to_disk()
        self.last_epoch_end_ts=datetime.now()

        async with self.mem_pool_condition:
            for transaction in self.mem_pool:
                if newBlock.transaction_exists_in_block(transaction):
                    self.mem_pool.remove(transaction)

        async with self.ipfs.file_hashes_lock:
            for hash in list(self.ipfs.file_hashes.keys()):
                if newBlock.cid_exists_in_block(hash):
                    self.ipfs.file_hashes.pop(hash, None)

    # ---------------- WALLET ----------------

    async def send_money(self, amount, receiver_public_key):

        if(amount <= 0):
            print("Invalid Amount\n")
            return

        if(amount > self.chain.calc_balance(self.wallet.public_key_pem, self.mem_pool, self.stakers)):
            print("Not Enough Balance\n")
            return

        await self.create_and_broadcast_transaction(amount, receiver_public_key)

    # ---------------- SMART CONTRACT ----------------

    async def deploy_contract(self, contract_code):

        cost = self.contract.get_deploy_cost(contract_code)

        payload = [contract_code, cost]

        if(cost > self.chain.calc_balance(self.wallet.public_key_pem, self.mem_pool, self.stakers)):
            print("Not Enough Balance\n")
            return

        receiver_public_key = "deploy"

        await self.create_and_broadcast_transaction(payload, receiver_public_key)

    async def invoke_contract(self, contract_id, func_name, args):

        cost, new_state = self.contract.get_invoke_cost_and_new_state(contract_id, func_name, args)

        payload = [contract_id, func_name, args, new_state, cost]

        if(cost > self.chain.calc_balance(self.wallet.public_key_pem, self.mem_pool, self.stakers)):
            print("Not Enough Balance\n")
            return

        receiver_public_key = "invoke"

        await self.create_and_broadcast_transaction(payload, receiver_public_key)

    # ---------------- STARTUP & TERMINATION ----------------

    async def run_forever(self):
        # Start background tasks
        self.consensus_task = asyncio.create_task(self.find_longest_chain())
        self.disc_task = asyncio.create_task(self.network.discover_peers())
        self.reset_task=asyncio.create_task(self.restart_epoch())
        self.sampler_task = asyncio.create_task(self.network.gossip_peer_sampler())

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

        self.last_epoch_end_ts=datetime.now()

        self.chain.add_genesis_black(self.wallet.public_key_pem, self.wallet.private_key)
        
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

        if self.consensus_task:
            self.consensus_task.cancel()

        if self.reset_task:
            self.reset_task.cancel()

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