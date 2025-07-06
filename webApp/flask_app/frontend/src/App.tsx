import { useState } from "react";
import Navbar from "./Components/Navbar";
// import axios from "axios";

function App() {
  const [showStartMenu, setShowStartMenu]=useState(false);
  const [showConnectMenu, setShowConnectMenu]=useState(false);
  const [name, setName]=useState("");
  const [port, setPort]=useState("");
  const [host, setHost]=useState("");
  const [bootStrapPort, setBootStrapPort]=useState("");
  // const getKeys=async ()=>{
  //   try{
  //     const res=await axios.get("/api/chain/create_keys");
  //     setSk(res.data.sk);
  //     setVk(res.data.vk);
  //     setLoggedIn(true);
  //   }
  //   catch{

  //   }
  // }

  const startMenu=()=>{
    if(!showStartMenu)
        return null;

    return(
      <div className="fixed inset-0 bg-black/50 z-5 flex justify-center items-center">
        <div className=" bg-secondary w-[30vw] rounded-2xl border-[3px] border-solid border-primary">
          <div className="bg-primary text-white text-center rounded-t-xl p-5">
            Fill These
          </div>
          <div className="content p-5">
            <div className="form flex flex-col items-center">
              <div className="nameInp flex my-5 md:my-3 flex-col items-start"> 
                <label htmlFor="" className="name font-orbitron">
                  Enter Name Of Node :
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="border-2 border-gray-500 bg-white px-4 py-2 w-[70vw] md:w-96 mb-5"
                  />
              </div>
              <div className="linkInp flex flex-col items-start mb-5"> 
                <label htmlFor="" className="name font-orbitron">
                  Enter the port to run node :
                </label>
                <input
                  type="text"
                  value={port}
                  onChange={(e) => setPort(e.target.value)}
                  className="border-2 border-gray-500 bg-white px-4 py-2 w-[70vw] md:w-96"
                  />
              </div>
            </div>
            <div className="buttons flex justify-around">
              <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3">
                Start Block Chain
              </button>
              <button className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{setShowStartMenu(false)}}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>  
    )
  }

  const connectMenu=()=>{
    if(!showConnectMenu)
        return null;

    return(
      <div className="fixed inset-0 bg-black/50 z-5 flex justify-center items-center">
        <div className=" bg-secondary w-[30vw] rounded-2xl border-[3px] border-solid border-primary">
          <div className="bg-primary text-white text-center rounded-t-xl p-5">
            Fill These
          </div>
          <div className="content p-5">
            <div className="form flex flex-col items-center">
              <div className="nameInp flex my-5 md:my-3 flex-col items-start"> 
                <label htmlFor="" className="name font-orbitron">
                  Enter Name Of Node :
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="border-2 border-gray-500 bg-white px-4 py-2 w-[70vw] md:w-96 mb-5"
                  />
              </div>
              <div className="linkInp flex flex-col items-start mb-5"> 
                <label htmlFor="" className="name font-orbitron">
                  Enter the port to run node :
                </label>
                <input
                  type="text"
                  value={port}
                  onChange={(e) => setPort(e.target.value)}
                  className="border-2 border-gray-500 px-4 bg-white py-2 w-[70vw] md:w-96"
                  />
              </div>
              <div className="linkInp flex flex-col items-start mb-5"> 
                <label htmlFor="" className="name font-orbitron">
                  Enter hostname of bootstrap node :
                </label>
                <input
                  type="text"
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                  className="border-2 bg-white border-gray-500 px-4 py-2 w-[70vw] md:w-96"
                  />
              </div>
              <div className="linkInp flex flex-col items-start mb-5"> 
                <label htmlFor="" className="name font-orbitron">
                  Enter port of bootstrap node :
                </label>
                <input
                  type="text"
                  value={bootStrapPort}
                  onChange={(e) => setBootStrapPort(e.target.value)}
                  className="border-2 border-gray-500 bg-white px-4 py-2 w-[70vw] md:w-96"
                  />
              </div>
            </div>
            <div className="buttons flex justify-around">
              <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3">
                Start Block Chain
              </button>
              <button className="account_tab bg-red-400 text-white p-5 rounded-2xl cursor-pointer m-3" onClick={()=>{setShowConnectMenu(false)}}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>  
    )
  }


  return (
    <>
      <Navbar/>
      <div className="bg-secondary h-[90vh] w-full flex flex-col justify-center items-center">
      <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3 w-[80vw] md:w-[15vw]" onClick={()=>{setShowStartMenu(true)}}>
        Start Block Chain
      </button>
      <button className="account_tab bg-primary text-white p-5 rounded-2xl cursor-pointer m-3 w-[80vw] md:w-[15vw]" onClick={()=>{setShowConnectMenu(true)}}>
        Connect To Block Chain
      </button>
      </div>
      {startMenu()}
      {connectMenu()}
      </>
  )
}

export default App