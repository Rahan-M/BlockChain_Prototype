import { useEffect, useState } from 'react'
import { IoReloadSharp } from "react-icons/io5";
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import axios from 'axios'

interface Peer {
    name: string;
    host: string;
    port: number;
    public_key: string;
}

const Run = () => {
    const {isRunning, loadingAuth}=useAuth();
    // const [showPowMenu, setShowPowMenu]=useState(false)
    // const [showPosMenu, setShowPosMenu]=useState(false)
    // const [showPoaMenu, setShowPoaMenu]=useState(false)
    const [name, setName]=useState("");
    const [port, setPort]=useState(-1);
    const [host, setHost]=useState("");
    const [vk, setVk]=useState("");
    const [sk, setSk]=useState("");
    const [accBal, setAccBalance]=useState(-1);
    const [showTxMenu1, setShowTxMenu1]=useState(false);
    const [showTxMenu2, setShowTxMenu2]=useState(false);
    const [peers, setPeers]=useState<Peer[]>([]);
    const [pubKey, setPubKey]=useState("");
    const [amt, setAmt]=useState(-1);
    
    const navigate=useNavigate()
    const {enqueueSnackbar}=useSnackbar()
    
    const fetchData=async()=>{
        const res=await axios.get("/api/pow/status")
        if(!res.data.success)
            return

        setName(res.data.name)
        setHost(res.data.host)
        setPort(res.data.port)
        setAccBalance(res.data.account_balance)
        setSk(res.data.private_key)
        setVk(res.data.public_key)
    }



    useEffect(() => {
        if(!isRunning){
            enqueueSnackbar("Create/Connect First", {variant:'warning'})
            navigate('/')
        }  
        // fetchData()
        // if(consensus=="pow"){
        //     setShowPowMenu(true);
        //     setShowPosMenu(false);
        //     setShowPoaMenu(false);
        // }
        // if(consensus=="pos"){
        //     setShowPosMenu(true);
        //     setShowPowMenu(false);
        //     setShowPoaMenu(false);
        // }
        // if(consensus=="poa"){
        //     setShowPoaMenu(true);
        //     setShowPosMenu(false);
        //     setShowPowMenu(false);
        // }
    }, [isRunning, loadingAuth])

    const addTransaction= async()=>{
        setShowTxMenu1(false);
        setShowTxMenu2(false);
        const res=await axios.post('/api/pow/transaction',{
            "public_key":pubKey,
            "amt":amt
        })
        if(!res.data.success){
            enqueueSnackbar("Failed to add transaction", {variant:'error'});
        }
        enqueueSnackbar("Added transaction succesfully", {variant:'success'});
    }   

    const fetchPeers = async () => {
        try {
            const res = await axios.get("/api/pow/peers");
            if (!res.data.success) {
                enqueueSnackbar("Failed to fetch known peers", { variant: "error" });
                return;
            }
            // Ensure data.known_peers is an array, default to empty if not
            const fetchedPeers = Array.isArray(res.data.known_peers) ? res.data.known_peers : [];
            setPeers(fetchedPeers);

            // Only set initial pubKey if peers were successfully fetched and exist
            if (fetchedPeers.length > 0) {
                setPubKey(fetchedPeers[0].public_key);
            } else {
                // Handle case where no peers are fetched (e.g., clear pubKey)
                setPubKey('');
                enqueueSnackbar("No known peers found.", { variant: "info" });
            }

        } catch (err) {
            enqueueSnackbar("Failed to fetch known peers", { variant: "error" });
            console.error("Error fetching peers:", err); // Log the actual error
        }
    };

    useEffect(() => {
        if ((showTxMenu1 || showTxMenu2)) {
            fetchPeers();
        }
    }, [showTxMenu1]); 

    const txMenu1=()=>{
        if(!showTxMenu1)
            return null;
        if(!peers)
            return null
        
        return(
            <div className="fixed inset-0 bg-black/50 z-5 flex justify-center items-center">
            <div className=" bg-secondary w-[30vw] rounded-2xl border-[3px] border-solid border-primary">
                <div className="bg-primary text-white text-center rounded-t-xl p-5">
                    Choose Whom to Send To
                </div>
                <div className="content p-5 flex flex-col gap-5 items-center">
                    <select name="peers" id="peer_opts" className='border-2 border-gray-500 bg-white px-4 py-2 w-[70vw] md:w-96' onChange={(e)=>{setPubKey(e.target.value)}}>
                        {peers.map((peer)=>(
                            <option key={peer.name} value={peer.public_key}>{peer.name}</option>
                        ))}
                    </select>
                    <div className="linkInp flex flex-col items-start mb-5"> 
                        <label htmlFor="" className="name font-orbitron">
                        Enter the amount to send :
                        </label>
                        <input
                        type="text"
                        onChange={(e) => setAmt(Number(e.target.value))}
                        className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                        />
                    </div>
                </div>
                <div className="buttons flex justify-around">
                    <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3" onClick={addTransaction}>
                        Add Transaction
                    </button>
                    <button className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{setShowTxMenu1(false)}}>
                        Cancel
                    </button>
                </div>
            </div>
            </div>  
        )
    }

    const txMenu2=()=>{
        if(!showTxMenu2)
            return null;
    
        if(!peers)
            return null;
        return(
            <div className="fixed inset-0 bg-black/50 z-5 flex justify-center items-center">
            <div className=" bg-secondary w-[30vw] rounded-2xl border-[3px] border-solid border-primary">
                <div className="bg-primary text-white text-center rounded-t-xl p-5">
                    Fill These
                </div>
                <div className="content p-5 flex flex-col items-center">
                    <div className="linkInp flex flex-col items-start mb-5"> 
                        <label htmlFor="" className="name font-orbitron">
                            Enter Public Key :
                        </label>
                        <input
                        type="text"
                        onChange={(e)=>{
                            let tempKey=`${e.target.value}\n`;  
                            const length=tempKey.length
                            if(length>50){
                                tempKey=tempKey.substring(0,26)+'\n'+tempKey.substring(27, length-26)+'\n'+tempKey.substring(length-25);
                            }
                            enqueueSnackbar("Not a valid public address", {variant:'error'});
                            // This is because the backend expects a newline charachter at 3 points in the public key.
                            // The library we are using (ecdsa) will otherwise see this as an invalid key
                            setPubKey(tempKey)
                        }}
                        className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                        />
                    </div>
                    <div className="linkInp flex flex-col items-start mb-5"> 
                        <label htmlFor="" className="name font-orbitron">
                            Enter the amount to send :
                        </label>
                        <input
                        type="text"
                        onChange={(e) => setAmt(Number(e.target.value))}
                        className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                        />
                    </div>
                </div>
                <div className="buttons flex justify-around">
                    <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3" onClick={addTransaction}>
                        Add Transaction
                    </button>
                    <button className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{setShowTxMenu2(false)}}>
                        Cancel
                    </button>
                </div>
            </div>
            </div>  
        )
    }

    const commonMenu=()=>{
        return(
                <div className="menu flex flex-col justify-center items-center h-[90vh] gap-5">
                    <div className="accBal flex items-center  bg-primary text-white p-5 rounded-xl">
                        <div className='mr-2 cursor-pointer' onClick={()=>setShowTxMenu1(true)}>
                            1. Add Transaction via saved name
                        </div>
                    </div>
                    <div className="accBal flex items-center  bg-primary text-white p-5 rounded-xl">
                        <div className='mr-2 cursor-pointer' onClick={()=>setShowTxMenu2(true)}>
                            2. Add Transaction via public address
                        </div>
                    </div>
                    {txMenu1()}
                    {txMenu2()}
                </div>
        )
    }

    const viewChainPage = () => {
        navigate('/chain');
    }
    
    const viewPendingTransactionsPage = () => {
        navigate('/pending');
    }
    
    const viewKnownPeersPage = () => {
        navigate('/peers');
    }
    
    return (
        <div className='flex bg-secondary justify-around'>
            <div className='options w-full'>
                {commonMenu()}
            </div>
            <div className='bg-tertiary w-2'></div>
            <div className='status w-full relative flex flex-col p-5 pt-20 gap-3'>
                <IoReloadSharp className='absolute top-5 right-5 text-2xl cursor-pointer' onClick={fetchData}/>
                <div>
                    Name : {name}
                </div>
                <div>
                    Host : {host}
                </div>
                <div>
                    Port : {port}
                </div>
                <div>
                    Account Balance : {accBal}
                </div>
                <div>
                    Private Key : {sk} 
                </div>
                <div>
                    Public Key : {vk}
                </div>
                <div className='cursor-pointer bg-primary p-3 w-[7vw] text-center text-white rounded-xl' onClick={viewChainPage}>
                    View Chain
                </div>
                <div className='cursor-pointer bg-primary p-3 w-[15vw] text-center text-white rounded-xl' onClick={viewPendingTransactionsPage}>
                    View Pending Transactions
                </div>
                <div className='cursor-pointer bg-primary p-3 w-[15vw] text-center text-white rounded-xl' onClick={viewKnownPeersPage}>
                    View Known Peers
                </div>
            </div>
        </div>
    )
}

export default Run