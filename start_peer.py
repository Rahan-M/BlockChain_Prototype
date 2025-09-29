import asyncio
from consensus.poa.p2p import Peer as PoAPeer
from consensus.pos.p2p import Peer as PoSPeer
from consensus.pow.p2p import Peer as PoWPeer
from consensus.pow.mal_node import Peer as PowMalPeer

def start_peer():
    host = "localhost"
    port = int(input("Enter Port: "))
    name = input("Enter Name: ")
    consensus = input("Enter Consensus[poa/pos/pow] (default : pow): ")
    activate_disk_load = input("Do you like to load saved data if any(y/n): ")
    activate_disk_save = input("Do you like to continuously backup data to disk(y/n): ")
    action = input("Enter 'create' to create a network and 'connect' to connect to a network (default: create): ")
    bootstrap_host = None
    bootstrap_port = None
    if action == "connect":
        bootstrap_host = input("Enter host to connect: ")
        bootstrap_port = int(input("Enter port to connect: "))
    peer = None
    if consensus == "poa":
        peer = PoAPeer(host, port, name, activate_disk_load, activate_disk_save)
        peer.name_to_node_id_dict[peer.name.lower()] = peer.node_id
        peer.node_id_to_name_dict[peer.node_id] = peer.name.lower()
    elif consensus == "pos":
        staker = None
        staker_raw_input = input("Staker? ").strip().lower()
        if staker_raw_input == "true":
            staker = True
        elif staker_raw_input == "false":
            staker = False
        peer = PoSPeer(host, port, name, staker, activate_disk_load, activate_disk_save)
    else:        
        mal=False
        mal_raw_input = input("Malcious? ").strip().lower()
        if mal_raw_input == "true":
            mal = True
        elif mal_raw_input == "false":
            mal = False
        
        if(not mal):
            miner = True
            miner_raw_input = input("Miner? ").strip().lower()
            if miner_raw_input == "true":
                miner = True
            elif miner_raw_input == "false":
                miner = False
            peer = PoWPeer(host, port, name, miner, activate_disk_load, activate_disk_save)
        else:
            peer = PowMalPeer(host, port, name, True, activate_disk_load, activate_disk_save)


    try:
        asyncio.run(peer.start(bootstrap_host, bootstrap_port))
    except KeyboardInterrupt:
        print("\nShutting Down...")

if __name__=="__main__":
    start_peer()