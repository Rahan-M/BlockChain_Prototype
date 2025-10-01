import asyncio
from consensus.poa.p2p import Peer as PoAPeer
from consensus.pos.p2p import Peer as PoSPeer
from consensus.pow.p2p import Peer as PoWPeer
from consensus.poa.mal_node import Peer as PoaMalPeer
from consensus.pos.mal_node import Peer as PosMalPeer
from consensus.pow.mal_node import Peer as PowMalPeer

def start_peer():
    host = input("Enter Host: ")
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
        mal=False
        mal_raw_input = input("Malcious? (y/n) ").strip().lower()
        if mal_raw_input == "y":
            mal = True
        elif mal_raw_input == "n":
            mal = False
        if(not mal):
            peer = PoAPeer(host, port, name, activate_disk_load, activate_disk_save)
        else:
            peer = PoaMalPeer(host, port, name, activate_disk_load, activate_disk_save)

    elif consensus == "pos":
        mal=False
        mal_raw_input = input("Malcious? (y/n) ").strip().lower()
        if mal_raw_input == "y":
            mal = True
        elif mal_raw_input == "n":
            mal = False
        
        if(not mal):
            staker = True
            staker_raw_input = input("Staker? (y/n) ").strip().lower()
            if staker_raw_input == "y":
                staker = True
            elif staker_raw_input == "n":
                staker = False
            peer = PoSPeer(host, port, name, staker, activate_disk_load, activate_disk_save)
        else:
            peer = PosMalPeer(host, port, name, True, activate_disk_load, activate_disk_save)

    else:        
        mal=False
        mal_raw_input = input("Malcious? (y/n) ").strip().lower()
        if mal_raw_input == "y":
            mal = True
        elif mal_raw_input == "n":
            mal = False
        
        if(not mal):
            miner = True
            miner_raw_input = input("Miner? (y/n) ").strip().lower()
            if miner_raw_input == "y":
                miner = True
            elif miner_raw_input == "n":
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