import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";
import axios from "axios";

interface Stake {
    id:string,
    name:string, // staker name if available
    staker:string, // staker public key
    amt:number,
    ts:number
}

const Stakes=()=>{
    const [stakes, setStakes]=useState<Stake[]>([]);
    const {enqueueSnackbar}=useSnackbar();
    const fetchStakes = async () => {
        try {
            const res = await axios.get("/api/pos/view_stakes")
            if (!res.data.success) {
                return;
            }

            setStakes(res.data.current_stakes);
        } catch (err) {
            enqueueSnackbar("Failed to fetch chain", { variant: "error" });
        }
    }

    useEffect(() => {
        fetchStakes();
    }, []);
    return(
        <div>
            {stakes.map((stake:Stake, index:number)=>(
                <div key={index} className="block border p-4 m-2 rounded bg-gray-100">
                        <p><strong>Stake ID:</strong> {stake.id}</p>
                        <p><strong>Staker: </strong> {stake.name}</p>
                        <p><strong>Staker Public Key: </strong> {stake.staker}</p>
                        <p><strong>Staked Amount: </strong> {stake.amt}</p>
                        <p><strong>Time Stamp: </strong>{stake.ts}</p>
                </div>
            ))}
        </div>
    )
}

export default Stakes