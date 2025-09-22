// psych-app/src/main.jsx

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';          // Tailwind layers
import { HeroUIProvider } from '@heroui/react';
import StripeProvider from './StripeProvider';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <StripeProvider>
      <HeroUIProvider>
        <App />
      </HeroUIProvider>
    </StripeProvider>
  </React.StrictMode>
);
