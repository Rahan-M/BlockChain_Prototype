import { useEffect, useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import axios from 'axios'

const Run = () => {
    const {isRunning}=useAuth()
    // const [showPowMenu, setShowPowMenu]=useState(false)
    // const [showPosMenu, setShowPosMenu]=useState(false)
    // const [showPoaMenu, setShowPoaMenu]=useState(false)
    const [accBal, setAccBalance]=useState(-1)
    const navigate=useNavigate()
    const {enqueueSnackbar}=useSnackbar()

    useEffect(() => {
        if(!isRunning){
            enqueueSnackbar("Create/Connect First", {variant:'warning'})
            navigate('/')
        }  
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
    }, [])

    const findAccBal=async ()=>{
        const res=await axios.get(`/api/pow/balance`);
        if(res.data.success){
            setAccBalance(res.data.account_balance)
        }else{
            enqueueSnackbar("Couldn't fetch account balance", {variant:'error'})
        }
    }

    const accBalance=()=>{
        if(accBal==-1)
            return null
        return(
            <div className='border-2 p-5 border-primary flex flex-col'>
                {accBal}
            </div>
        )
    }

    const commonMenu=()=>{
        return(
            <div className="menu flex justify-center items-center h-[90vh] bg-secondary">
                <div className="accBal bg-primary text-white p-5 rounded-xl" onClick={findAccBal}>1. Find Account Balance</div>
                {accBalance()}
            </div>
        )
    }
    
    return (
        <>
            {commonMenu()}
        </>
    )
}

export default Run