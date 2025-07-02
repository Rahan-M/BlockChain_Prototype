import { useState } from "react";
import Navbar from "./Components/Navbar";
import axios from "axios";

function App() {
  const [sk, setSk]=useState("");
  const [vk, setVk]=useState("");
  const [loggedIn, setLoggedIn]=useState(false);

  const getKeys=async ()=>{
    try{
      const res=await axios.get("http://localhost:5020/create_keys");
      setSk(res.data.sk);
      setVk(res.data.vk);
      setLoggedIn(true);
    }
    catch{

    }
  }

  const getKeysButton=()=>{
    return(
      <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer" onClick={getKeys}>
        Create Keys
      </button>
    )
  }

  const displayKeys=()=>{
    return(
      <div className="keys">
        <div className="vk">
          {vk}
        </div>
        <div className="sk">
          {sk}
        </div>
      </div>
    )
  }

  return (
    <>
      <Navbar/>
      <div className="bg-secondary h-[90vh] w-full flex justify-center items-center">
        {!loggedIn && getKeysButton()}
        {loggedIn && displayKeys()}
      </div>
      </>
  )
}

export default App
