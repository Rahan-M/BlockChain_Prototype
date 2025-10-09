import { useEffect, useState } from 'react';
import { useSnackbar } from 'notistack';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';

const States = () => {
    const [states, setStates] = useState([]);
    const {consensus}=useAuth();
    const { enqueueSnackbar } = useSnackbar();

    const fetchStates = async () => {
        try {
            const res = await axios.get(`/api/${consensus}/states`)
            if (!res.data.success) {
                return;
            }

            setStates(res.data.states);
        } catch (err) {
            enqueueSnackbar("Failed to fetch states", { variant: "error" });
        }
    }

    useEffect(() => {
        fetchStates();
    }, []);

    type StateDict = Record<any, any>;

    interface State{
        id:string,
        state:StateDict,
    }

    type StatesViewerProps = {
        states: State[];
    };

    const StatesViewer = ({ states }: StatesViewerProps) => {
        return (
            <div className="states-container">
                {states.map((state: State, index: number) => (
                    <div key={index} className="state border p-4 m-2 rounded bg-gray-100">
                        <p><strong>Contract ID:</strong> {state.id}</p>

                        <div className="state-container mt-2">
                            <p className="font-semibold">Contract State:</p>
                            <div className="code border p-2 mt-1 bg-white rounded">
                                {Object.entries(state.state).map(([key, value]) => (
                                    <p>{key}: {value}</p>
                                ))}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        );
    };

    return (
        <div>
            <StatesViewer states={states} />
        </div>
    );
}

export default States;