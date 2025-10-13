//psych-app/src/App.jsx

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import AuthProvider from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Register from './pages/Register';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import TestStart from './pages/TestStart';
import TestRunner from './pages/TestRunner';
import Results from './pages/Results';
import PaymentElementPage from './pages/PaymentElementPage';
import SubscriptionPage from './pages/Subscription';




export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Navbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/register" element={<Register />} />
          <Route path="/login" element={<Login />} />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/test/start/:testId" element={<TestStart />} />
          <Route path="/test/:resultId" element={<TestRunner />} />
          <Route path="/results/:resultId" element={<Results />} />


          <Route path="/pay/:resultId" element={<PaymentElementPage />} />

          <Route
            path="/subscription"
            element={
              <ProtectedRoute>
                <SubscriptionPage />
              </ProtectedRoute>
            }
          />

        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

