import React, {useEffect, useState, useContext, createContext} from 'react'
import type { ReactNode } from 'react';

interface AuthContextType {
    isRunning: boolean;
    consensus: string | null;
    loadingAuth:boolean;
    admin: boolean;
    login: (consensus: string, isAdmin?: boolean)=>void;
    logout: ()=>void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [isRunning, setIsRunning] = useState<boolean>(false);
    const [consensus, setConsensus] = useState<string | null>(null);
    const [loadingAuth, setLoadingAuth]=useState<boolean>(true);
    const [admin, setAdmin] = useState<boolean>(false);

    useEffect(()=>{
        const storedIsRunning=localStorage.getItem('isRunning');
        const storedConsensus=localStorage.getItem('consensus');
        const storedAdmin = localStorage.getItem('admin');

        if(!(storedIsRunning && storedConsensus))
            return;
        try{
            const parsedIsRunning=JSON.parse(storedIsRunning);
            const parsedAdmin = storedAdmin ? JSON.parse(storedAdmin) : false;
            setIsRunning(parsedIsRunning);
            setConsensus(storedConsensus);
            setAdmin(parsedAdmin);
        }
        catch (err){
            console.error("Error while parsing,",err);
            localStorage.removeItem('isRunning');
            localStorage.removeItem('consensus');
            localStorage.removeItem('admin');
        } 
        setLoadingAuth(false);
    }, [])

    const login=(consensus: string, isAdmin: boolean = false)=>{
        if(!consensus) return;
        setConsensus(consensus);
        setIsRunning(true);
        setAdmin(isAdmin);
        localStorage.setItem('isRunning', JSON.stringify(true));
        localStorage.setItem('consensus', consensus);
        localStorage.setItem('admin', JSON.stringify(isAdmin));
        console.log("Logged In");
    }

    const logout=()=>{
        setConsensus(null);
        setIsRunning(false);
        setAdmin(false);
        localStorage.removeItem('consensus');
        localStorage.removeItem('isRunning');
        localStorage.removeItem('admin');
    }
    const value = {consensus, isRunning, loadingAuth, admin, login, logout };

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