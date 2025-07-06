import React, {useEffect, useState, useContext, createContext} from 'react'
import type { ReactNode } from 'react';

interface AuthContextType {
    isRunning: boolean;
    consensus: string | null;
    loadingAuth:boolean
    login: (consensus: string)=>void;
    logout: ()=>void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [isRunning, setIsRunning] = useState<boolean>(false);
    const [consensus, setConsensus] = useState<string | null>(null);
    const [loadingAuth, setLoadingAuth]=useState<boolean>(true);

    useEffect(()=>{
        const storedIsRunning=localStorage.getItem('isRunning');
        const storedConsensus=localStorage.getItem('consensus');
        if(!(storedIsRunning && storedConsensus))
            return;
        try{
            const parsedIsRunning=JSON.parse(storedIsRunning);
            setIsRunning(parsedIsRunning);
            setConsensus(storedConsensus);
        }
        catch (err){
            console.error("Error while parsing,",err);
            localStorage.removeItem('isRunning');
            localStorage.removeItem('consensus');
        } 
        setLoadingAuth(false);
    }, [])

    const login=(consensus: string)=>{
        if(!consensus) return;
        setConsensus(consensus);
        setIsRunning(true);
        localStorage.setItem('isRunning', JSON.stringify(true));
        localStorage.setItem('consensus', consensus);
        console.log("Logged In");
    }

    const logout=()=>{
        setConsensus(null);
        setIsRunning(false);
        localStorage.removeItem('consensus');
        localStorage.removeItem('isRunning');
    }
    const value = {consensus, isRunning, loadingAuth, login, logout };

    return (
      <AuthContext.Provider value={value}>
        {children}
      </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
      throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
  };