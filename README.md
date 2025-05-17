# Blockchain Prototype

A terminal-based blockchain implementation in Python with peer-to-peer networking, mining, transaction validation and account-based architecture.

## Features

- ⛓️ Peer-to-peer network with decentralized communication
- 🔑 Public/private key-based account system
- ✅ Digital signature verification for transactions
- ⚖️ Consensus mechanism to validate blocks
- ⛏️ Block mining with proof-of-work
- 🖥️ CLI-based interaction

## Getting Started

### Prerequisites

- Python 3.10+
- `pip` (Python package manager)
- venv (for creating virtual environments)

### Installation

Clone project into your local machine
```bash
git clone https://github.com/Rahan-M/BlockChain_Prototype.git
```
Enter into the project folder
```bash
cd BlockChain_Prototype
```
Create and activate virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```
Install dependencies
```bash
pip install -r requirements.txt
```

### Running the Project

To create the first node in the network, run
```bash
python p2p.py --name Rahan --port 5000 --miner True
```
To launch additinal nodes in the network, run:
```bash
python p2p.py --name Jefin --port 5001 --miner False --connect localhost:5000
```
What it does?
- Name attribute assigns the name of the account holder
- Port attribute specifies the port the node should listen to
- Miner attribute enables or disables mining capability for the node
- Connect attribute specifies the address and port of the node to connect to

## How It Works

### Basic Structure

Each **node** contains its own set of
- Known peers list (members of the network)
- Client connections (connection established by your node to other nodes)
- Server connections (connection established by other nodes to your node)
- Wallet (acts as your account in the network)
- Transaction pool (contains all transactions pending to be mined)
- Chain (personal copy of the blockchain)

Each **account** contains
- Private key
- Public key

Each **transaction** contains
- Public key of the sender
- Public key of the receiver
- Transaction amount

Each **block** contains
- Timestamp
- List of transactions
- Hash of previous block
- Current block hash
- Nonce (proof-of-work)

### Handshake Protocol

- Client: Sends ping
- Server: Receives ping &rightarrow; sends pong
- Client: Receives pong &rightarrow; Sends peer info (information about itself)
- Server: Receives peer info &rightarrow; adds it to its known peers (if not already present) &rightarrow; sends back known_peers (list of all nodes it knows)
- Client: Receives known_peers &rightarrow; adds new peers to its own known_peers &rightarrow; requests the blockchain
- Server: Receives chain request &rightarrow; sends its current chain
- Client: Receives the chain &rightarrow; replaces its own if the length of new chain is longer than or equal to the current one

### Transaction Flow

Users can initiate transactions between nodes. Each transaction:
- Is signed using the sender's private key
- Is broadcast to all connected peers
- Waits in a transaction pool until mined

### Mining and Consensus

-   A new block is mined every 1 minute, if there are pending transactions in the transaction pool
-   Mining nodes collect transactions into a block
-   A basic Proof-of-Work algorithm is applied to find a valid hash
-   Once mined, the block is broadcast to the network
-   All nodes validate the block before adding it to their chain

### Peer-to-Peer Networking

If the total number of nodes in the network is less than 10, it forms a mesh network. If the node count exceeds 9, Gossip-based Random Peer Sampling is used
- Each node maintains a list of 8 connected peers
- At regular intervals, a node drops one connection and connects to a new, previously unconnected peer from the known peers list
- This prevents network congestion by limiting the number of connections per node
- It also prevents sub-network formation by randomly switching connections

### Blockchain Integrity

-   Each block contains a reference to the previous block’s hash
-   Nodes verify chain validity before accepting new blocks
-   Tampering is detected by hash mismatches or invalid signatures

## Authors

**Rahan M**
[GitHub](https://github.com/Rahan-M) | [LinkedIn](https://www.linkedin.com/in/rahan-m-077a32254?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app)

**Jefin Joji**
[GitHub](https://github.com/JefinCodes) | [LinkedIn](https://www.linkedin.com/in/jefin-joji-659354313?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app)