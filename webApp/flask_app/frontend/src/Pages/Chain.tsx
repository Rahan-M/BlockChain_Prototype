import { useEffect, useState } from 'react';
import { useSnackbar } from 'notistack';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

const Chain = () => {
    const [chain, setChain] = useState([]);
    const {consensus}=useAuth();
    const { enqueueSnackbar } = useSnackbar();

    const fetchChain = async () => {
        try {
            const res = await axios.get(`/api/${consensus}/chain`)
            if (!res.data.success) {
                return;
            }

            setChain(res.data.chain);
        } catch (err) {
            enqueueSnackbar("Failed to fetch chain", { variant: "error" });
        }
    }

    useEffect(() => {
        fetchChain();
    }, []);

    interface Transaction {
        id: string;
        ts: string;
        sender: string;
        receiver: string;
        amount: number;
    }

    interface File {
        cid: string;
        desc: string;
    }

    interface Stake{
        id:string,
        staker:string,
        amt:number,
        ts:string,
        sign:string
    }

    interface Block {
        id: string;
        ts: string;
        prevhash: string;
        hash: string;
        nonce?: number;
        miner: string;
        transactions: Transaction[];
        files: File[];
        stakes?: Stake[];
        staked_amt?:number;
        vrf_proof?:string;
        seed?:string;
        miner_node_id?: string;
        miner_public_key?: string;
    }

    type ChainViewerProps = {
        chain: Block[];
    };

    const ChainViewer = ({ chain }: ChainViewerProps) => {
        return (
            <div className="chain-container">
                {chain.map((block: Block, index: number) => (
                    <div key={index} className="block border p-4 m-2 rounded bg-gray-100">
                        <p><strong>Block ID:</strong> {block.id}</p>
                        <p><strong>Timestamp:</strong> {block.ts}</p>
                        <p><strong>Previous Hash:</strong> {block.prevhash}</p>
                        <p><strong>Hash:</strong> {block.hash}</p>
                        {consensus=='pow' && <p><strong>Nonce:</strong> {block.nonce}</p>}
                        {consensus === 'pos' && <p><strong>Staker:</strong> {block.miner}</p>} 
                        {consensus === 'pow' && <p><strong>Miner:</strong> {block.miner}</p>}
                        {consensus === 'poa' && <p><strong>Miner Node ID:</strong> {block.miner_node_id}</p>}
                        {consensus === 'poa' && <p><strong>Miner Public Key:</strong> {block.miner_public_key}</p>}
                        {consensus=='pos' && <p><strong>Staked Amount:</strong> {block.staked_amt}</p>}
                        {block.vrf_proof && <p><strong>Vrf Proof:</strong> {block.vrf_proof}</p>}
                        {block.seed && <p><strong>Seed:</strong> {block.seed}</p>}

                        <div className="transactions mt-2">
                            <p className="font-semibold underline">Transactions:</p>
                            {block.transactions.map((tx, txIndex) => (
                                <div key={txIndex} className="tx border p-2 mt-1 bg-white rounded">
                                    <p>ID: {tx.id}</p>
                                    <p>Timestamp: {tx.ts}</p>
                                    <p>Sender: {tx.sender}</p>
                                    <p>Receiver: {tx.receiver}</p>
                                    <p>Amount: {tx.amount}</p>
                                </div>
                            ))}
                        </div>

                        {block.files.length > 0 && (
                            <div className="files mt-2">
                                <p className="font-semibold underline">Files:</p>
                                {block.files.map((file, fileIndex) => (
                                    <div key={fileIndex} className="file border p-2 mt-1 bg-white rounded">
                                        <p>CID: {file.cid}</p>
                                        <p>Description: {file.desc}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                        {block.stakes && block.stakes.length>0 &&
                            <div className="Stakes mt-2">
                                <p className="font-semibold underline">Stakes:</p>
                                {block.stakes.map((stake, idx) => (
                                    <div key={idx} className="file border p-2 mt-1 bg-white rounded">
                                        <p>Id: {stake.id}</p>
                                        <p>Staker: {stake.staker}{stake.staker==block.miner && <h1>Winner!!!</h1>}</p>
                                        <p>Amount: {stake.amt}</p>
                                        <p>Timestamp: {stake.ts}</p>
                                        <p>Sign: {stake.sign}</p>
                                    </div>
                                ))}
                            </div>
                        }
                    </div>
                ))}
            </div>
        );
    };

    return (
        <div>
            <ChainViewer chain={chain} />
        </div>
    );
}

export default Chain;