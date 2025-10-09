import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import Run from './Pages/Run.tsx'
import Chain from './Pages/Chain.tsx'
import Mempool from './Pages/Mempool.tsx'
import Peers from './Pages/Peers.tsx'
import Contracts from './Pages/Contracts.tsx'
import States from './Pages/States.tsx'
import RootLayout from './layouts/RootLayout.tsx'
import {AuthProvider} from './contexts/AuthContext.tsx'
import {createBrowserRouter, RouterProvider} from 'react-router-dom'
import { SnackbarProvider } from 'notistack'
import Stakes from './Pages/Stakes.tsx'
import Miners from './Pages/Miners.tsx'

const NotFound = () => (
  <div className="min-h-screen bg-black flex items-center justify-center">
      <span className="text-white text-center text-6xl md:text-8xl font-bold lg:text-nowrap -translate-y-24">
          404 - Page Not Found
      </span>
  </div>
);

const router = createBrowserRouter([
  {
      path: "/",
      element: <RootLayout />,
      children: [
          { index: true, element: <App /> },
          { path: '/run', element: <Run /> },
          { path: '/chain', element: <Chain /> },
          { path: '/pending', element: <Mempool /> },
          { path: '/peers', element: <Peers /> },
          { path: '/contracts', element: <Contracts /> },
          { path: '/states', element: <States /> },
          { path: '/stakes', element: <Stakes /> },
          { path: '/miners', element: <Miners /> },
          { path: "*", element: <NotFound /> }
      ],
  },
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <SnackbarProvider maxSnack={3} anchorOrigin={{ vertical: 'top', horizontal: 'center' }}>
        <RouterProvider router={router} />
      </SnackbarProvider>
    </AuthProvider>
  </StrictMode>,
)
