import { useEffect, useState } from 'react';
import { useSnackbar } from 'notistack';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

const Miners = () => {
    const {consensus}=useAuth();
    const [miners, setMiners] = useState([]);
    const { enqueueSnackbar } = useSnackbar();

    const fetchMiners = async () => {
        try {
            const res = await axios.get(`/api/${consensus}/miners`)
            if (!res.data.success) {
                return;
            }

            setMiners(res.data.current_miners);
        } catch (err) {
            enqueueSnackbar("Failed to fetch miners", { variant: "error" });
        }
    }

    useEffect(() => {
        fetchMiners();
    }, []);

    interface Miner {
        name: string;
        node_id: string;
        public_key: string;
    }

    type MinersViewerProps = {
        miners: Miner[];
    };

    const MinersViewer = ({ miners }: MinersViewerProps) => {
        return (
            <div className="miners-container">
                {miners.map((miner, minerIndex) => (
                    <div key={minerIndex} className="miner border p-4 m-2 bg-gray-100 rounded">
                        <p><strong>Miner {minerIndex}</strong></p>
                        <p><strong>Name:</strong> {miner.name}</p>
                        <p><strong>Node ID:</strong> {miner.node_id}</p>
                        <p><strong>Public Key:</strong> {miner.public_key}</p>
                    </div>
                ))}
            </div>
        );
    };

    return (
        <div>
            <MinersViewer miners={miners} />
        </div>
    );
}

export default Miners;