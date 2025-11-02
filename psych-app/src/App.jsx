//psych-app/src/App.jsx

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AuthProvider from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Register from './pages/Register';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import TestStart from './pages/TestStart';
import TestRunner from './pages/TestRunner';
import AltTestRunner from './pages/AltTestRunner';
import Results from './pages/Results';
import PaymentElementPage from './pages/PaymentElementPage';
import SubscriptionPage from './pages/Subscription';




export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
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
          <Route path="/test/start/:testId/alt" element={<TestStart useAltRunner />} />
          <Route path="/test/:resultId" element={<TestRunner />} />
          <Route path="/test/:resultId/alt" element={<AltTestRunner />} />
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

