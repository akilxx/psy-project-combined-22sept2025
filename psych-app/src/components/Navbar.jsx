// psych-app/src/components/Navbar.jsx


import { Link } from 'react-router-dom';
import { ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline';
import useAuth from '../hooks/useAuth';


export default function Navbar() {
  const { user, logout } = useAuth();
  return (
    <nav className="flex items-center justify-between px-6 py-3 bg-transparent text-primary">
      <Link to="/" className="text-xl font-semibold">Big5Test</Link>
      <div className="flex gap-4 items-center">
        {user && (
          <>
            <Link to="/subscription" className="text-sm font-medium hover:text-indigo-600">
              Subscription
            </Link>
            <span className="text-sm text-slate-600">{user.email}</span>
          </>
        )}
        {user ? (
          <button onClick={logout} className="flex items-center gap-1">
            <ArrowRightOnRectangleIcon className="w-5 h-5" /> Logout
          </button>
        ) : (
          <Link to="/login">Login / Register</Link>
        )}
      </div>
    </nav>
  );
}
