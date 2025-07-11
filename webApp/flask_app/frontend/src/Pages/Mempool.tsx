import { useEffect, useState } from 'react';
import { useSnackbar } from 'notistack';
import axios from 'axios';

const Mempool = () => {
    const [mempool, setMempool] = useState([]);

    const { enqueueSnackbar } = useSnackbar();

    const fetchMempool = async () => {
        try {
            const res = await axios.get("/api/pow/pending")
            if (!res.data.success) {
                return;
            }

            setMempool(res.data.pending_transactions);
        } catch (err) {
            enqueueSnackbar("Failed to fetch mempool", { variant: "error" });
        }
    }

    useEffect(() => {
        fetchMempool();
    }, []);

    interface Transaction {
        id: string;
        ts: string;
        sender: string;
        receiver: string;
        amount: number;
    }

    type MempoolViewerProps = {
        mempool: Transaction[];
    };

    const MempoolViewer = ({ mempool }: MempoolViewerProps) => {
        return (
            <div className="mempool-container">
                {mempool.map((tx, txIndex) => (
                    <div key={txIndex} className="tx border p-4 m-2 bg-gray-100 rounded">
                        <p><strong>ID:</strong> {tx.id}</p>
                        <p><strong>Timestamp:</strong> {tx.ts}</p>
                        <p><strong>Sender:</strong> {tx.sender}</p>
                        <p><strong>Receiver:</strong> {tx.receiver}</p>
                        <p><strong>Amount:</strong> {tx.amount}</p>
                    </div>
                ))}
            </div>
        );
    };

    return (
        <div>
            <MempoolViewer mempool={mempool} />
        </div>
    );
}

export default Mempool;