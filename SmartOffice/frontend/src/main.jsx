import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';
import { LanguageProvider } from './context/LanguageContext';
import FieldAssist from './components/FieldAssist';
import GlobalDrop from './components/GlobalDrop';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <LanguageProvider>
      <App />
      <FieldAssist />
      <GlobalDrop />
    </LanguageProvider>
  </React.StrictMode>
);
