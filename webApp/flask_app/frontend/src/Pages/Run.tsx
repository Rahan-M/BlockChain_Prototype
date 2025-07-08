import { useEffect, useState } from 'react'
import { IoIosArrowBack } from "react-icons/io";
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
            <div className="menu flex flex-col justify-center items-center h-[90vh] bg-secondary">
                <div className="accBal flex items-center  bg-primary text-white p-5 rounded-xl" onClick={()=>{
                    if(accBal==-1)
                        findAccBal()
                    else 
                        setAccBalance(-1)
                }}>
                    <div className='mr-2' >
                        1. Find Account Balance    
                    </div>
                    <IoIosArrowBack id='arrowIcon' />
                </div>
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