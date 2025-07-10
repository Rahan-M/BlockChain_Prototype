import { useEffect, useState } from 'react';
import { useSnackbar } from 'notistack';
import axios from 'axios';

const Chain = () => {
    const [chain, setChain] = useState([]);

    const { enqueueSnackbar } = useSnackbar();

    const fetchChain = async () => {
        try {
            const res = await axios.get("/api/pow/chain")
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

    interface Block {
        id: string;
        ts: string;
        prevhash: string;
        hash: string;
        nonce: number;
        miner: string;
        transactions: Transaction[];
        files: File[];
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
                        <p><strong>Nonce:</strong> {block.nonce}</p>
                        <p><strong>Miner:</strong> {block.miner}</p>

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