import { useEffect, useState } from 'react'
import { IoIosArrowBack } from "react-icons/io";
import { IoReloadSharp } from "react-icons/io5";
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import axios from 'axios'

const Run = () => {
    const {isRunning, loadingAuth}=useAuth()
    // const [showPowMenu, setShowPowMenu]=useState(false)
    // const [showPosMenu, setShowPosMenu]=useState(false)
    // const [showPoaMenu, setShowPoaMenu]=useState(false)
    const [name, setName]=useState("")
    const [port, setPort]=useState(-1)
    const [host, setHost]=useState("")
    const [vk, setVk]=useState("")
    const [sk, setSk]=useState("")
    const [accBal, setAccBalance]=useState(-1)

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
    }, [loadingAuth])

    const findAccBal=async ()=>{
        const res=await axios.get(`/api/pow/balance`);
        if(res.data.success){
            setAccBalance(res.data.account_balance)
        }else{
            enqueueSnackbar("Couldn't fetch account balance", {variant:'error'})
        }
        
    }
    
    const accBalance=()=>{
        const icon=document.getElementById('arrowIcon')
        const rotationClass='rotate-[-90deg]'
        if(accBal==-1){
            if(icon?.classList.contains(rotationClass))
                icon.classList.remove(rotationClass)
            return null
        }
        
        if(icon && !icon.classList.contains(rotationClass))
            icon.classList.add('rotate-[-90deg]');

        return(
            <div className='border-2 p-5 border-primary flex flex-col'>
                Account Balance {accBal}
            </div>
        )
    }

    const commonMenu=()=>{
        return(
                <div className="menu flex flex-col justify-center items-center h-[90vh]">
                    <div className="accBal flex items-center  bg-primary text-white p-5 rounded-xl" onClick={()=>{
                        if(accBal==-1)
                            findAccBal()
                        else 
                        setAccBalance(-1)
                    }}>
                        <div className='mr-2' >
                            1. Find Account Balance    
                        </div>
                        <IoIosArrowBack />
                    </div>
                    {accBalance()}
                </div>
        )
    }

    const viewChainPage = () => {
        navigate('/chain');
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
                <div className='cursor-pointer bg-primary p-3 w-[15vw] text-center text-white rounded-xl'>
                    View Pending Transactions
                </div>
                <div className='cursor-pointer bg-primary p-3 w-[15vw] text-center text-white rounded-xl'>
                    View Known Peers
                </div>
            </div>
        </div>
    )
}

export default Run