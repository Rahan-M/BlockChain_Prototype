import { useEffect, useState } from 'react'
import { IoReloadSharp } from "react-icons/io5";
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import { IoIosCloseCircle } from "react-icons/io";
import axios from 'axios'

interface Peer {
    name: string;
    host: string;
    port: number;
    public_key: string;
}

const Run = () => {
    const {isRunning, loadingAuth, consensus, admin}=useAuth();
    // const [showPowMenu, setShowPowMenu]=useState(false)
    // const [showPosMenu, setShowPosMenu]=useState(false)
    // const [showPoaMenu, setShowPoaMenu]=useState(false)
    const [name, setName]=useState("");
    const [port, setPort]=useState(-1);
    const [host, setHost]=useState("");
    const [vk, setVk]=useState("");
    const [sk, setSk]=useState("");
    const [tsle, setTsle]=useState(-1);
    const [accBal, setAccBalance]=useState(-1);
    const [showTxMenu1, setShowTxMenu1]=useState(false);
    const [showTxMenu2, setShowTxMenu2]=useState(false);
    const [showUploadMenu, setShowUploadMenu]=useState(false);
    const [showDownloadMenu, setShowDownloadMenu]=useState(false);
    const [showStopConfirmation, setShowStopConfirmation]=useState(false);
    const [showDepMenu, setShowDepMenu]=useState(false);
    const [showInvokeMenu, setShowInvokeMenu]=useState(false);

    const [peers, setPeers]=useState<Peer[]>([]);
    const [pubKey, setPubKey]=useState("");
    const [amt, setAmt]=useState(-1);
    
    const [fileName, setFileName]=useState("");
    const [fileCid, setFileCid]=useState("");
    const [filePath, setFilePath]=useState("");
    const [fileDesc, setFileDesc]=useState("");

    const [contractCode, setContractCode]=useState("");
    const [contractId, setContractId]=useState("");
    const [funcName, setFuncName]=useState("");
    const [args, setArgs]=useState<string[]>([]);

    const[stakeAmt, setStakeAmt]=useState(0);
    const[showStakePopup, setShowStakePopup]=useState(false);

    const[showAddMinerPopup, setShowAddMinerPopup]=useState(false);
    const[showRemoveMinerPopup, setShowRemoveMinerPopup]=useState(false);

    const[nodeId, setNodeId]=useState("");
    const[adminId, setAdminId]=useState("");

    const[addNodeId, setAddNodeId]=useState("");
    const[removeNodeId, setRemoveNodeId]=useState("");
    const[laminers, setLaminers]=useState([]);
    const[nlaminers, setNlaminers]=useState([]);

    const navigate=useNavigate()
    const {enqueueSnackbar}=useSnackbar()
    
    const fetchData=async()=>{
        const res=await axios.get(`/api/${consensus}/status`)
        if(!res.data.success)
            return

        setName(res.data.name)
        setHost(res.data.host)
        setPort(res.data.port)
        setAccBalance(res.data.account_balance)
        setSk(res.data.private_key)
        setVk(res.data.public_key)
        if(res.data.tsle)
            setTsle(res.data.tsle)
        if(consensus == "poa"){
            setNodeId(res.data.node_id)
            setAdminId(res.data.admin_id)
        }
    }

    useEffect(() => {
        if(loadingAuth) return;

        if(!isRunning || !consensus){
            enqueueSnackbar("Create/Connect First", {variant:'warning'});
            navigate('/');
            return;
        }

        console.log("Consensus in Run:", consensus);
        fetchData();
        // if(!isRunning){
        //     enqueueSnackbar("Create/Connect First", {variant:'warning'})
        //     navigate('/')
        // }  
        // console.log(isRunning);
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
    }, [isRunning, loadingAuth, consensus]);

    const addTransaction= async()=>{
        setShowTxMenu1(false);
        setShowTxMenu2(false);
        const res=await axios.post(`/api/${consensus}/transaction`,{
            "public_key":pubKey,
            "payload":amt
        })
        if(!res.data.success){
            enqueueSnackbar("Failed to add transaction", {variant:'error'});
        }
        enqueueSnackbar("Added transaction succesfully", {variant:'success'});
    }   

    const uploadFile= async()=>{
        setShowUploadMenu(false);
        const res=await axios.post(`/api/ipfs/uploadFile`,{
            "desc":fileDesc,
            "path":filePath
        })
        if(!res.data.success){
            enqueueSnackbar("Failed to add transaction", {variant:'error'});
        }
        enqueueSnackbar("Added transaction succesfully", {variant:'success'});
    }  

    const downloadFile= async()=>{
        setShowDownloadMenu(false);
        const res=await axios.post(`/api/ipfs/downloadFile`,{
            "cid":fileCid,
            "path":filePath,
            "name":fileName
        })
        if(!res.data.success){
            enqueueSnackbar("Failed to add transaction", {variant:'error'});
        }
        enqueueSnackbar("Added transaction succesfully", {variant:'success'});
    }   

    const fetchPeers = async () => {
        try {
            const res = await axios.get(`/api/${consensus}/peers`);
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

    const uploadMenu=()=>{
        if(!showUploadMenu)
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
                            Enter Description Of The File :
                        </label>
                        <input
                        type="text"
                        onChange={(e)=>{
                            setFileDesc(e.target.value);
                        }}
                        className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                        />
                    </div>
                    <div className="linkInp flex flex-col items-start mb-5"> 
                        <label htmlFor="" className="name font-orbitron">
                            Enter the Absolute Path of The File :
                        </label>
                        <input
                        type="text"
                        onChange={(e) => setFilePath(e.target.value)}
                        className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                        />
                    </div>
                </div>
                <div className="buttons flex justify-around">
                    <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3" onClick={uploadFile}>
                        Upload File
                    </button>
                    <button className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{setShowUploadMenu(false)}}>
                        Cancel
                    </button>
                </div>
            </div>
            </div>  
        )
    }

    const downloadMenu=()=>{
        if(!showDownloadMenu)
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
                            Enter Cid Of The File :
                        </label>
                        <input
                        type="text"
                        onChange={(e)=>{
                            setFileCid(e.target.value)
                        }}
                        className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                        />
                    </div>
                    <div className="linkInp flex flex-col items-start mb-5"> 
                        <label htmlFor="" className="name font-orbitron">
                            Enter the path :
                        </label>
                        <input
                        type="text"
                        onChange={(e) => setFilePath(e.target.value)}
                        className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                        />
                    </div>
                    <div className="linkInp flex flex-col items-start mb-5"> 
                        <label htmlFor="" className="name font-orbitron">
                            Enter the name of the file :
                        </label>
                        <input
                        type="text"
                        onChange={(e) => setFileName(e.target.value)}
                        className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                        />
                    </div>
                </div>
                <div className="buttons flex justify-around">
                    <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3" onClick={downloadFile}>
                        Download File
                    </button>
                    <button className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{setShowDownloadMenu(false)}}>
                        Cancel
                    </button>
                </div>
            </div>
            </div>  
        )
    }

    const stopConfirmation=()=>{
        if(!showStopConfirmation)
            return null;
    
        return(
            <div className="fixed inset-0 bg-black/50 z-5 flex justify-center items-center">
            <div className=" bg-secondary w-[30vw] rounded-2xl border-[3px] border-solid border-primary">
                <div className="bg-primary text-white text-center rounded-t-xl p-5">
                    Are You Sure You Want to Stop Participating in this Blockchain?
                </div>
                <div className="buttons flex justify-around">
                    <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{console.log('Hey')}}>
                        Yes
                    </button>
                    <button className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{setShowStopConfirmation(false)}}>
                        No
                    </button>
                </div>
            </div>
            </div>  
        )
    }

    const invokeContract=async()=>{
        setShowDepMenu(false);
        const res=await axios.post(`/api/${consensus}/transaction`,{
            "public_key":'invoke',
            "payload":[contractId, funcName, args]
        })
        if(!res.data.success){
            enqueueSnackbar("Failed to invoke contract", {variant:'error'});
        }
        enqueueSnackbar("Contract Invoked Successfully", {variant:'success'});
    }

    const invokeMenu = () => {
        if (!showInvokeMenu) return null;

        return (
            <div className="fixed inset-0 bg-black/50 z-50 flex justify-center items-center">
                <div className="bg-secondary w-[30vw] rounded-2xl border-[3px] border-solid border-primary">
                    <div className="bg-primary text-white text-center rounded-t-xl p-5">
                        Fill These
                    </div>
                    <div className="content p-5 flex flex-col items-center">
                        
                        {/* Contract ID */}
                        <div className="linkInp flex flex-col items-start mb-5"> 
                            <label className="name font-orbitron">Enter Contract Id :</label>
                            <input
                                type="text"
                                onChange={(e) => setContractId(e.target.value)}
                                className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                            />
                        </div>

                        {/* Function Name */}
                        <div className="linkInp flex flex-col items-start mb-5"> 
                            <label className="name font-orbitron">Enter the Function Name :</label>
                            <input
                                type="text"
                                onChange={(e) => setFuncName(e.target.value)}
                                className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                            />
                        </div>

                        {/* Dynamic Arguments */}
                        {args.map((arg, index) => (
                            <div key={index} className="linkInp flex flex-col items-start mb-3">
                                <label className="name font-orbitron">Enter Argument {index + 1} :</label>
                                <div className='flex items-center'>
                                    <input
                                        type="text"
                                        value={arg}
                                        onChange={(e) => {
                                            const newArgs = [...args];
                                            newArgs[index] = e.target.value;
                                            setArgs(newArgs);
                                        }}
                                        className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                                    />
                                    <IoIosCloseCircle
                                        onClick={() => {
                                            const newArgs = args.filter((_, i) => i !== index);
                                            setArgs(newArgs);
                                        }}
                                        className="cursor-pointer text-2xl text-tertiary bg-white"
                                    />
                                </div>
                            </div>
                        ))}

                        {/* Add Argument Button */}
                        <button
                            className="bg-tertiary text-white px-4 py-2 rounded-xl mb-5"
                            onClick={() => setArgs([...args, ""])}
                        >
                            + Add Argument
                        </button>
                    </div>

                    {/* Action Buttons */}
                    <div className="buttons flex justify-around">
                        <button
                            className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3"
                            onClick={invokeContract}
                        >
                            Invoke Contract
                        </button>
                        <button
                            className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3"
                            onClick={() => setShowInvokeMenu(false)}
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        );
    };

    const deployContract=async()=>{
        setShowDepMenu(false);
        const res=await axios.post(`/api/${consensus}/transaction`,{
            "public_key":'deploy',
            "payload":[contractCode]
        })
        if(!res.data.success){
            enqueueSnackbar("Failed to deploy contract", {variant:'error'});
        }
        enqueueSnackbar("Contract Deployed Successfully", {variant:'success'});
    }

    const depMenu = () => { // Menu for smart contract deployment
        if (!showDepMenu)
            return null;

        return (
            <div className="fixed inset-0 bg-black/50 z-5 flex justify-center items-center">
                <div className=" bg-secondary w-[40vw] rounded-2xl border-[3px] border-solid border-primary">
                    <div className="bg-primary text-white text-center rounded-t-xl p-5">
                        Fill These
                    </div>
                    <div className="content p-5 flex flex-col items-center">
                        <div className="linkInp flex flex-col items-start mb-5"> 
                            <label htmlFor="" className="name font-orbitron">
                                Enter Code :
                            </label>
                            <textarea
                            defaultValue={`# Write our smart contract's function here (in python)
def function_name(parameter1, parameter2, parameter3, state):
    # your code here
    return state, 'some message'`}                                onChange={(e) => {
                                    setContractCode(e.target.value);
                                }}
                                className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-[35vw] h-[50vh] resize-none"
                            />
                        </div>
                    </div>
                    <div className="buttons flex justify-around">
                        <button
                            className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3"
                            onClick={deployContract}
                        >
                            Deploy Contract
                        </button>
                        <button
                            className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3"
                            onClick={() => { setShowDepMenu(false) }}
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            </div>  
        )
    }

    const fileMenu=()=>{
        return(
            <>
            <div className='self-start px-20'>
                <h1 className='text-2xl'>File Menu</h1>
            </div>
            <div className="flex items-center  bg-primary text-white p-5 rounded-xl">
                <div className='mr-2 cursor-pointer' onClick={()=>setShowUploadMenu(true)}>
                    Upload File
                </div>
            </div>
            <div className="flex items-center  bg-primary text-white p-5 rounded-xl">
                <div className='mr-2 cursor-pointer' onClick={()=>setShowDownloadMenu(true)}>
                    Download File
                </div>
            </div>
            </>
        )
    }

    const txMenu=()=>{
        return(
            <>
            <div className='self-start px-20'>
                <h1 className='text-2xl'>Transaction Menu</h1>
            </div>
            <div className="accBal flex items-center  bg-primary text-white p-5 rounded-xl">
                <div className='mr-2 cursor-pointer' onClick={()=>setShowTxMenu1(true)}>
                    Add Transaction via saved name
                </div>
            </div>
            <div className="flex items-center  bg-primary text-white p-5 rounded-xl">
                <div className='mr-2 cursor-pointer' onClick={()=>setShowTxMenu2(true)}>
                    Add Transaction via public address
                </div>
            </div>
            </>
        )
    }

    const scMenu=()=>{
        return(
            <>
            <div className='self-start px-20'>
                <h1 className='text-2xl'>Smart Contract Menu</h1>
            </div>
            <div className="accBal flex items-center  bg-primary text-white p-5 rounded-xl">
                <div className='mr-2 cursor-pointer' onClick={()=>setShowDepMenu(true)}>
                    Deploy Contract
                </div>
            </div>
            <div className="flex items-center  bg-primary text-white p-5 rounded-xl">
                <div className='mr-2 cursor-pointer' onClick={()=>setShowInvokeMenu(true)}>
                    Invoke Contract
                </div>
            </div>
            </>
        )
    }

    const commonMenu=()=>{
        return(
                <div className="menu flex flex-col justify-center items-center h-[90vh] gap-5">
                    {txMenu()}
                    {fileMenu()}
                    {scMenu()}
                    <div className='self-start px-20'>
                        <h1 className='text-2xl'>Danger Zone</h1>
                    </div>
                    <div className="flex items-center  bg-primary text-white p-5 rounded-xl">
                        <div className='mr-2 cursor-pointer' onClick={()=>setShowStopConfirmation(true)}>
                            Stop 
                        </div>
                    </div>
                    {txMenu1()}
                    {txMenu2()}
                    {stopConfirmation()}
                    {uploadMenu()}
                    {downloadMenu()}
                    {depMenu()}
                    {invokeMenu()}
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
    
    const sendStake=async()=>{
        setShowStakePopup(false);
        const res=await axios.post("/api/pos/stake",{
            "amount":stakeAmt
        })
        if(!res.data.success){
            enqueueSnackbar("Failed to set stake", {variant:'error'});
        }
        enqueueSnackbar("Set stake succesfully", {variant:'success'});
    }

    const stakePopup=()=>{
        if(!showStakePopup)
            return null;
        
        return(
            <div className="fixed inset-0 bg-black/50 z-5 flex justify-center items-center">
            <div className=" bg-secondary w-[30vw] rounded-2xl border-[3px] border-solid border-primary">
                <div className="bg-primary text-white text-center rounded-t-xl p-5">
                    Select amount to stake
                </div>
                <div className="content p-5 flex flex-col gap-5 items-center">
                    <div className="linkInp flex flex-col items-start mb-5"> 
                        <label htmlFor="" className="name font-orbitron">
                        Enter the amount to send :
                        </label>
                        <input
                        type="text"
                        onChange={(e) => setStakeAmt(Number(e.target.value))}
                        className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                        />
                    </div>
                </div>
                <div className="buttons flex justify-around">
                    <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3" onClick={sendStake}>
                        Stake
                    </button>
                    <button className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{setShowStakePopup(false)}}>
                        Cancel
                    </button>
                </div>
            </div>
            </div>  
        )
    }

    const posMenu=()=>{
        return(
            <div className='flex flex-col justify-center items-center gap-5'>
                <div className='self-start px-20'>
                    <h1 className='text-2xl'>POS Menu</h1>
                </div>
                <div className="accBal flex items-center  bg-primary text-white p-5 rounded-xl">
                    <div className='mr-2 cursor-pointer' onClick={()=>setShowStakePopup(true)}>
                        Set Stake
                    </div>
                </div>
                {stakePopup()}
            </div>
        )
    }

    const fetchNotLatestMinersList = async () => {
        try {
            const res = await axios.get(`/api/poa/nlaminers`);
            if (!res.data.success) {
                enqueueSnackbar("Failed to fetch not latest miners", { variant: "error" });
                return;
            }
            // Ensure data.nlaminers is an array, default to empty if not
            const fetchedNlaminers = Array.isArray(res.data.nlaminers) ? res.data.nlaminers : [];
            setNlaminers(fetchedNlaminers);

            // Only set initial addNodeId if peers were successfully fetched and exist
            if (fetchedNlaminers.length > 0) {
                setAddNodeId(fetchedNlaminers[0].node_id);
            } else {
                // Handle case where no peers are fetched (e.g., clear pubKey)
                setAddNodeId('');
                enqueueSnackbar("No not latest miners found.", { variant: "info" });
            }

        } catch (err) {
            enqueueSnackbar("Failed to fetch not latest miners", { variant: "error" });
            console.error("Error fetching not latest miners:", err); // Log the actual error
        }
    };

    useEffect(() => {
        if (showAddMinerPopup) {
            fetchNotLatestMinersList();
        }
    }, [showAddMinerPopup]); 

    const addMiner=async()=>{
        setShowAddMinerPopup(false);
        const res=await axios.post("/api/poa/add",{
            "node_id":addNodeId
        })
        if(!res.data.success){
            enqueueSnackbar("Failed to add miner", {variant:'error'});
        }
        enqueueSnackbar("Miner added successfully", {variant:'success'});
    }

    interface Miner{
        name:string,
        node_id:string,
        public_key:string
    }

    const addMinerPopup=()=>{
        if(!showAddMinerPopup)
            return null;
        
        return(
            <div className="fixed inset-0 bg-black/50 z-5 flex justify-center items-center">
                <div className=" bg-secondary w-[30vw] rounded-2xl border-[3px] border-solid border-primary">
                    <div className="bg-primary text-white text-center rounded-t-xl p-5">
                        Choose Whom to Add
                    </div>
                    <div className="content p-5 flex flex-col gap-5 items-center">
                        <select name="nlaminers" id="nlaminers_opts" className='border-2 border-gray-500 bg-white px-4 py-2 w-[70vw] md:w-96' onChange={(e)=>{setAddNodeId(e.target.value)}}>
                            {nlaminers.map((nlaminer: Miner)=>(
                                <option key={nlaminer.name} value={nlaminer.node_id}>{nlaminer.name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="buttons flex justify-around">
                        <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3" onClick={addMiner}>
                            Add Miner
                        </button>
                        <button className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{setShowAddMinerPopup(false)}}>
                            Cancel
                        </button>
                    </div>
                </div>
            </div>  
        )
    }

    const fetchLatestMinersList = async () => {
        try {
            const res = await axios.get(`/api/poa/laminers`);
            if (!res.data.success) {
                enqueueSnackbar("Failed to fetch latest miners", { variant: "error" });
                return;
            }
            // Ensure data.laminers is an array, default to empty if not
            const fetchedLaminers = Array.isArray(res.data.laminers) ? res.data.laminers : [];
            setLaminers(fetchedLaminers);

            // Only set initial addNodeId if peers were successfully fetched and exist
            if (fetchedLaminers.length > 0) {
                setRemoveNodeId(fetchedLaminers[0].node_id);
            } else {
                // Handle case where no peers are fetched (e.g., clear pubKey)
                setRemoveNodeId('');
                enqueueSnackbar("No latest miners found.", { variant: "info" });
            }

        } catch (err) {
            enqueueSnackbar("Failed to fetch latest miners", { variant: "error" });
            console.error("Error fetching latest miners:", err); // Log the actual error
        }
    };

    useEffect(() => {
        if (showRemoveMinerPopup) {
            fetchLatestMinersList();
        }
    }, [showRemoveMinerPopup]); 

    const removeMiner=async()=>{
        setShowRemoveMinerPopup(false);
        const res=await axios.post("/api/poa/remove",{
            "node_id":removeNodeId
        })
        if(!res.data.success){
            enqueueSnackbar("Failed to remove miner", {variant:'error'});
        }
        enqueueSnackbar("Miner removed successfully", {variant:'success'});
    }

    const removeMinerPopup=()=>{
        if(!showRemoveMinerPopup)
            return null;
        
        return(
            <div className="fixed inset-0 bg-black/50 z-5 flex justify-center items-center">
                <div className=" bg-secondary w-[30vw] rounded-2xl border-[3px] border-solid border-primary">
                    <div className="bg-primary text-white text-center rounded-t-xl p-5">
                        Choose Whom to Remove
                    </div>
                    <div className="content p-5 flex flex-col gap-5 items-center">
                        <select name="laminers" id="laminers_opts" className='border-2 border-gray-500 bg-white px-4 py-2 w-[70vw] md:w-96' onChange={(e)=>{setRemoveNodeId(e.target.value)}}>
                            {laminers.map((laminer: Miner)=>(
                                <option key={laminer.name} value={laminer.node_id}>{laminer.name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="buttons flex justify-around">
                        <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3" onClick={removeMiner}>
                            Remove Miner
                        </button>
                        <button className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{setShowRemoveMinerPopup(false)}}>
                            Cancel
                        </button>
                    </div>
                </div>
            </div>  
        )
    }

    const poaMenu=()=>{
        return(
            <div className='flex flex-col justify-center items-center gap-5'>
                <div className='self-start px-20'>
                    <h1 className='text-2xl'>POA Menu</h1>
                </div>
                <div className="flex items-center  bg-primary text-white p-5 rounded-xl">
                    <div className='mr-2 cursor-pointer' onClick={()=>setShowAddMinerPopup(true)}>
                        Add Miner
                    </div>
                    <div className='mr-2 cursor-pointer' onClick={()=>setShowRemoveMinerPopup(true)}>
                        Remove Miner
                    </div>
                </div>
                {addMinerPopup()}
                {removeMinerPopup()}
            </div>
        )
    }

    return (
        <div className='flex bg-secondary justify-around'>
            <div className='options w-full'>
                {commonMenu()}
                {consensus=='pos' && posMenu()}
                {consensus=='poa' && admin && poaMenu()}
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
                { consensus == "poa" &&
                    <div>
                        Node ID : {nodeId}
                    </div>
                }
                { consensus == "poa" &&
                    <div>
                        Admin ID : {adminId}
                    </div>
                }
                <div>
                    Private Key : {sk} 
                </div>
                <div>
                    Public Key : {vk}
                </div>
                {tsle!=-1 &&<div>
                    Time Since Last Epoch : {tsle}
                </div>}
                <div className='cursor-pointer bg-primary p-3 w-[7vw] text-center text-white rounded-xl' onClick={viewChainPage}>
                    View Chain
                </div>
                <div className='cursor-pointer bg-primary p-3 w-[15vw] text-center text-white rounded-xl' onClick={viewPendingTransactionsPage}>
                    View Pending Transactions
                </div>
                <div className='cursor-pointer bg-primary p-3 w-[15vw] text-center text-white rounded-xl' onClick={viewKnownPeersPage}>
                    View Known Peers
                </div>
                { consensus == "pos" &&
                    <div className='cursor-pointer bg-primary p-3 w-[15vw] text-center text-white rounded-xl' onClick={()=>navigate('/stakes')}>
                        View Current Stakes
                    </div>
                }
                { consensus == "poa" &&
                    <div className='cursor-pointer bg-primary p-3 w-[15vw] text-center text-white rounded-xl' onClick={()=>navigate('/miners')}>
                        View Current Miners
                    </div>
                }
            </div>
        </div>
    )
}

export default Run