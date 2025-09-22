//psych-app/src/api/auth.js

import api from './axios';

// Registration
export const register = email =>
  api.post('/register/', { email });

export const verifyRegister = ({ registration_id, otp_code }) =>
  api.post('/verify-registration/', { registration_id, otp_code });

// Login (OTP)
export const requestOtp = email =>
  api.post('/request-otp/', { email });

export const verifyOtp   = ({ email, otp_code }) =>
  api.post('/verify-otp/', { email, otp_code });
