import base64
import hashlib

from datetime import datetime, timedelta

from ecdsa import (
    VerifyingKey,
    BadSignatureError,
)

from webApp.blockchain.handlers.base_handler import BaseHandler

MAX_OUTPUT = 2**256
EPOCH_TIME = 60

class VrfThresholdException(Exception):
    pass

class PoSBlockHandler(BaseHandler):

    async def handle(self, websocket, msg):
        new_block_dict = msg.get("block")
        vrf_proof_str = msg.get("vrf_proof")
        sign_str = msg.get("sign")
        
        if not new_block_dict or not vrf_proof_str or not sign_str:
            return
        
        if "creator" not in new_block_dict:
            return
        
        newBlock = self.peer.block_dict_to_block(new_block_dict)

        if not self.peer.chain.isValidBlock(newBlock):
            print("\nInvalid Block\n")
            return
        
        try:
            # Convert Unix timestamp to datetime
            if isinstance(newBlock.ts, (int, float)):
                block_time = datetime.fromtimestamp(newBlock.ts)
            elif isinstance(newBlock.ts, str):
                block_time = datetime.fromisoformat(newBlock.ts)
            elif isinstance(newBlock.ts, datetime):
                block_time = newBlock.ts
            else:
                print("\nInvalid Block (unknown timestamp format)\n")
                return

            current_time = datetime.now()

            # Check block isn't from the future (with tolerance for clock skew)
            if block_time > current_time + timedelta(seconds=10):
                print("\nInvalid Block (timestamp in future)\n")
                return

            # Check block isn't too old
            if block_time < current_time - timedelta(seconds=EPOCH_TIME * 2):
                print("\nInvalid Block (timestamp too old)\n")
                return

            # Verify minimum time since last block
            if len(self.peer.chain.chain) > 0:
                last_block_ts = self.peer.chain.chain[-1].ts
                # Handle the same types for lastBlock timestamp
                if isinstance(last_block_ts, (int, float)):
                    last_block_time = datetime.fromtimestamp(last_block_ts)
                elif isinstance(last_block_ts, str):
                    last_block_time = datetime.fromisoformat(last_block_ts)
                elif isinstance(last_block_ts, datetime):
                    last_block_time = last_block_ts
                else:
                    print("\nInvalid Block (cannot validate timing against last block)\n")
                    return
                    
                time_diff = (block_time - last_block_time).total_seconds()
                
                # Blocks shouldn't come faster than the staking registration period
                if time_diff < EPOCH_TIME * 5/6:
                    print(f"\nInvalid Block (created too quickly: {time_diff}s < {EPOCH_TIME * 5/6}s)\n")
                    return
        except (ValueError, AttributeError, TypeError, OSError) as e:
            print(f"\nInvalid Block (bad timestamp format): {e}\n")
            return
        
        try:
            vk = VerifyingKey.from_pem(new_block_dict["creator"])
            vrf_proof = base64.b64decode(vrf_proof_str)
            sign = base64.b64decode(sign_str)
        except Exception as e:
            print(f"\nInvalid Block (encoding error): {e}\n")
            return

        print(f"\n{new_block_dict}\n")
        try:
            try:
                vk.verify(vrf_proof, self.peer.chain.epoch_seed().encode())
            except BadSignatureError as e:
                print(f"\nInvalid Block (VRF_PROOF Signature Error) {e}\n")
                return

            try:
                vk.verify(sign, str(newBlock).encode())
            except BadSignatureError as e:
                print(f"\nInvalid Block (Block Signature Error) {e}\n")
                return
            
            if newBlock.seed != self.peer.chain.epoch_seed():
                print("\nSeed May Have Been Altered\n")
                return

            newBlock.sign = sign
            vrf_output = hashlib.sha256(vrf_proof).hexdigest()
            vrf_output_int = int(vrf_output, 16)
            
            creator_key = new_block_dict["creator"]
            if creator_key not in self.peer.current_stakers:
                print("\nInvalid Block (creator not in current stakers)\n")
                return
            
            staked_amt = self.peer.current_stakers[creator_key]
            total_amt_staked = sum(self.peer.current_stakers.values())

            total_amt_staked_2 = 0
            for stake in newBlock.stakers:
                vk = VerifyingKey.from_pem(stake.staker)
                try:
                    print(f"\n{str(stake)}\n")
                    vk.verify(stake.sign, str(stake).encode())
                except BadSignatureError as e:
                    print(f"\nInvalid Block (Stake Signature Error) {e}\n")
                    return

                total_amt_staked_2 += stake.amt

            if total_amt_staked > total_amt_staked_2:
                print(f"\nSome stakes may have been ignored stakes_in_block 1:{total_amt_staked} 2:{total_amt_staked_2}\n")
                return

            threshold = (staked_amt / total_amt_staked_2) * MAX_OUTPUT
            if vrf_output_int >= threshold:
                raise VrfThresholdException("VRF_Output is not less than threshold")
            newBlock.seed = self.peer.chain.epoch_seed()
            newBlock.vrf_output = vrf_output
            newBlock.vrf_proof = vrf_proof

        except VrfThresholdException as e:
            print(f"\nInvalid Block (VRF_OUTPUT>THRESHOLD), {e}\n")
            return

        newBlock.creator = new_block_dict["creator"]
        self.peer.chain.chain.append(newBlock)
        print("\n\n Block Appended \n\n")
        self.peer.last_epoch_end_ts = datetime.now()

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
        
        self.peer.staked_amt = 0
        async with self.peer.curr_stakers_condition:
            self.peer.current_stakers.clear()
            self.peer.current_stakes.clear()

        await self.peer.network.broadcast_message(msg)
        self.peer.save_chain_to_disk()
