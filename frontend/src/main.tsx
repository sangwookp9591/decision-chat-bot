import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Shell } from './App';
import './styles/tokens.css';
import './style.css';

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><Shell /></BrowserRouter></React.StrictMode>);
