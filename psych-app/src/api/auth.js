//psych-app/src/api/auth.js

import api from './axios';

// Combined OTP flow
export const startOtpFlow = email =>
  api.post('/otp/', { email });

export const verifyOtp = ({ email, otp_code }) =>
  api.post('/otp/', { email, otp_code });
