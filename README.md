# Blockchain App
A web and terminal blockchain implementation in Python from scratch

## Features
- Peer-to-Peer network with decentralized communication
- Public/private key-based account system
- Digital signature verification
- Selectable consensus mechanism - PoW, PoS, PoA
- Smart contract deployment
- IPFS integration
- Persistent storage
- Malicious node to test security
- Command line & web interface

## Contents
- [Theory](#-theory)
- [About this project](#-about-this-project)
- [How to run this project](#-how-to-run-this-project)

## Theory
### What is blockchain?
A blockchain is a decentralized, distributed digital ledger where data is stored in blocks linked together in a chain
- A block is made of list of transactions
### Peer-to-Peer Network
Since, there is no central authority, network is formed in a peer-to-peer fashion.
### Consensus Mechanism
Blockchain involves transactions in a trustless environment. So there is need for a mechanism to ensure integrity of the chain. There comes the need of consensus mechanisms. Each consensus mechanism ensures integrity of the chain in their own way.
#### Proof of Work(PoW)
- Nodes compete to solve a cryptographic puzzle
- The winner gets to add the next block to the chain
#### Proof of Stake(PoS)
#### Proof of Authority(PoA)
- A limited set of trusted nodes(authorities) validate and create new blocks
### Smart Contracts
- A smart contract is like a digital agreement written in code
- It sits on the blockchain and runs automatically when certain rules are met
### IPFS
Blockchains are not designed for storing large amount of data. That's where IPFS comes in.
- It's a decentralized file storage system
- Each file is identified by its content
- A unique hash called CID(Content Identifiers) is generated based on the content(Files with same content will have same CID)
- IPFS uses a Distributed Hash Table(DHT), similar to BitTorrent's Kademlia DHT
- When you request a CID, your node queries the DHT to ask "Which peers are providing this CID?"
- Nodes that have previously announced that CID to the DHT will be returned as providers
- Your node then directly connects to those providers via IPFS's peer-to-peer transport protocols(libp2p)

## About this project
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

**Transactions** are of 3 types

- **Coin Transaction** - To transfer money
  - Timestamp
  - Public key of the sender
  - Public key of the receiver
  - Transaction amount
- **Deploy Transaction** - To deploy contract
  - Timestamp
  - Public key of the sender
  - Contract code
  - Deploy charge

- **Invoke Transaction** - To invoke contract
  - Timestamp  
  - Public key of the sender  
  - Contract ID  
  - Function name  
  - Arguments  
  - New state  
  - Invoke charge  

Each **block** contains
- Timestamp
- List of transactions
- Hash of previous block
- Current block hash
- Miner info
- List of files
### Handshake Protocol
- Client: Sends ping
- Server: Receives ping &rightarrow; sends pong
- Client: Receives pong &rightarrow; Sends peer info (information about itself)
- Server: Receives peer info &rightarrow; adds it to its known peers (if not already present) &rightarrow; sends back known_peers (list of all nodes it knows)
- Client: Receives known_peers &rightarrow; adds new peers to its own known_peers &rightarrow; requests the chain
- Server: Receives chain request &rightarrow; sends its current chain
- Client: Receives the chain &rightarrow; replaces its own if the length of new chain is longer than the current one
### Peer-to-Peer Network
If the total number of nodes in the network is less than 10, it forms a mesh network. If the node count exceeds 9, Gossip-based Random Peer Sampling is used
- Each node maintains a list of 8 connected peers
- At regular intervals, a node drops one connection and connects to a new, previously unconnected peer from the known peers list
- This prevents network congestion by limiting the number of connections per node
- It also prevents sub-network formation by randomly switching connections  

**Implemented Using:** python websockets, asyncio
### Consensus Mechanism
Users can select their prefered consensus mechanism from the list of three available
#### Proof of Work(PoW)
- A new block is mined every 30 secs, if there are pending transactions in the transaction pool
- Mining nodes collect transactions into a block
- Node that first finds a valid hash gets the chance to mine
- Difficulty is set to 5. That means, a valid hash is the one which starts with five zeroes
- Nonce is incremented until finding a valid hash
- Once mined, the block is broadcasted to the network
- All nodes validate the block before adding it to their chain
#### Proof of Stake(PoS)
#### Proof of Authority(PoA)
- Initially, admin, the one who started the chain is the only miner
- Admin can add or remove miners
- Each block can be mined only by the assigned miner
- If that miner is inactive, mining will be handed over to the next miner
### Smart Contracts
In this project
- Smart Contracts are written in python
- Users can write their own smart contracts and deploy
- Users can also invoke the deployed contract using their deployed address
- They run inside a sandboxed environment with time limit, memory limit and operation limit  

**Implemented Using:** RestrictedPython, multiprocessing
### IPFS
IPFS is integrated as a wrapper for the existing IPFS network. IPFS hashes of the user uploaded files are stored in the blocks. Other users can use this to download the file.  

**Implemented Using:** IPFS
### Persistent Storage
Persistent storage is implemented to enable nodes to reconnect to the network using there previous network data
### Malicious Node
### Web Interface

## How to run this project
### Prerequisites
- `python 3.10+`
- `pip` (python package manager)
- `venv` (for creating virtual environment)
### Installation & Setup
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
### Terminal App
Start terminal app
```bash
python start_peer.py
```
### Web App
Install frontend dependencies
```bash
cd webApp\flask_app\frontend
npm install
```
Build react app
```bash
npm run build
```
Start web app
```bash
cd ..\..
python run.py --port 5000
```
Open browser and visit http://0.0.0.0:5000

## Authors

**Rahan M**
[GitHub](https://github.com/Rahan-M) | [LinkedIn](https://www.linkedin.com/in/rahan-m-077a32254?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app)

**Jefin Joji**
[GitHub](https://github.com/JefinCodes) | [LinkedIn](https://www.linkedin.com/in/jefin-joji-659354313?utm_source=share&utm_campaign=share_via&utm_content=profile&utm_medium=android_app)