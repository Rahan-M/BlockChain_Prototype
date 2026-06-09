import base64
import json

from webApp.blockchain.handlers.base_handler import BaseHandler
from webApp.blockchain.blockchain_structures.pos.stake import Stake

class StakeAnnouncementHandler(BaseHandler):

    async def handle(self, websocket, msg):
        
        stake_str = msg["stake"]

        try:
            stake_dict = json.loads(stake_str)
        except json.JSONDecodeError:
            print("Invalid stake JSON")
            return

        if not stake_dict:
            return

        if not all(k in stake_dict for k in ["staker", "amt", "ts", "id", "sign_b64"]):
            return

        try:
            sign = base64.b64decode(stake_dict["sign_b64"])
        except Exception:
            print("\nInvalid signature encoding\n")
            return
        
        stake = Stake(stake_dict["staker"], stake_dict["amt"], stake_dict["id"], stake_dict["ts"], sign)

        if not stake.is_valid_stake(self.peer):
            print("Invalid stake\n")
            return
        
        async with self.peer.curr_stakers_condition:
            self.peer.current_stakes.add(stake)
            self.peer.current_stakers[stake.staker] = int(stake.amt)
            print(f"New stake : {stake.staker}:{stake.amt}")
        
        await self.peer.network.broadcast_message(msg)