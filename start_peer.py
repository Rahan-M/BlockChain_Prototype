import asyncio
from consensus.poa.p2p import Peer as PoAPeer
from consensus.pos.p2p import Peer as PoSPeer
from consensus.pow.p2p import Peer as PoWPeer

def start_peer():
    host = "localhost"
    port = int(input("Enter Port: "))
    name = input("Enter Name: ")
    consensus = input("Enter Consensus[poa/pos/pow] (default : pow): ")
    action = input("Enter 'create' to create a network and 'connect' to connect to a network (default: create): ")
    bootstrap_host = None
    bootstrap_port = None
    if action == "connect":
        bootstrap_host = input("Enter host to connect: ")
        bootstrap_port = int(input("Enter port to connect: "))
    peer = None
    if consensus == "poa":
        peer = PoAPeer(host, port, name)
        peer.name_to_node_id_dict[peer.name.lower()] = peer.node_id
        peer.node_id_to_name_dict[peer.node_id] = peer.name.lower()
    elif consensus == "pos":
        staker = None
        staker_raw_input = input("Staker? ").strip().lower()
        if staker_raw_input == "true":
            staker = True
        elif staker_raw_input == "false":
            staker = False
        peer = PoSPeer(host, port, name, staker)
    else:
        miner = None
        miner_raw_input = input("Miner? ").strip().lower()
        if miner_raw_input == "true":
            miner = True
        elif miner_raw_input == "false":
            miner = False
        peer = PoWPeer(host, port, name, miner)

    try:
        asyncio.run(peer.start(bootstrap_host, bootstrap_port))
    except KeyboardInterrupt:
        print("\nShutting Down...")

if __name__=="__main__":
    start_peer()