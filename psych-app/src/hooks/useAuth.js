//  psych-app/src/hooks/useAuth.js

import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
export default () => useContext(AuthContext);
