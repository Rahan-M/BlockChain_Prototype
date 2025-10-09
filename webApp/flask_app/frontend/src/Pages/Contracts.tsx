import { useEffect, useState } from 'react';
import { useSnackbar } from 'notistack';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

const Contracts = () => {
    const [contracts, setContracts] = useState([]);
    const {consensus}=useAuth();
    const { enqueueSnackbar } = useSnackbar();

    const fetchContracts = async () => {
        try {
            const res = await axios.get(`/api/${consensus}/contracts`)
            if (!res.data.success) {
                return;
            }

            setContracts(res.data.contracts);
        } catch (err) {
            enqueueSnackbar("Failed to fetch contracts", { variant: "error" });
        }
    }

    useEffect(() => {
        fetchContracts();
    }, []);

    interface Contract{
        id:string,
        code:string,
    }

    type ContractsViewerProps = {
        contracts: Contract[];
    };

    const ContractsViewer = ({ contracts }: ContractsViewerProps) => {
        return (
            <div className="contracts-container">
                {contracts.map((contract: Contract, index: number) => (
                    <div key={index} className="contract border p-4 m-2 rounded bg-gray-100">
                        <p><strong>Contract ID:</strong> {contract.id}</p>

                        <div className="code-container mt-2">
                            <p className="font-semibold">Contract Code:</p>
                            <div className="code border p-2 mt-1 bg-white rounded">
                                <p>{contract.code}</p>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        );
    };

    return (
        <div>
            <ContractsViewer contracts={contracts} />
        </div>
    );
}

export default Contracts;