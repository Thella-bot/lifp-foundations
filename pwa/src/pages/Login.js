import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api';

function Login() {
  const [uin, setUin] = useState('USER_0001');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async () => {
    try {
      await login(uin);
      navigate('/dashboard');
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>LIFP</h1>
      <input value={uin} onChange={e => setUin(e.target.value)} placeholder="Enter UIN" />
      <button onClick={handleLogin}>Login with MOSIP</button>
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
}
export default Login;