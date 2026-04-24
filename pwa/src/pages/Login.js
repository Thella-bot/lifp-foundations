import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api';

function Login() {
  const [uin, setUin] = useState('USER_0001');
  const [userType, setUserType] = useState('individual');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async () => {
    try {
      await login(uin, userType);
      navigate('/dashboard');
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div style={{ padding: 20, maxWidth: 400, margin: '0 auto' }}>
      <h1>LIFP</h1>
      <p>Login with your National ID</p>
      <input value={uin} onChange={e => setUin(e.target.value)} placeholder="USER_XXXX" />
      
      <div style={{ margin: '15px 0' }}>
        <label>
          <input
            type="radio"
            value="individual"
            checked={userType === 'individual'}
            onChange={() => setUserType('individual')}
          />
          Personal
        </label>
        <label style={{ marginLeft: 20 }}>
          <input
            type="radio"
            value="business"
            checked={userType === 'business'}
            onChange={() => setUserType('business')}
          />
          Business
        </label>
      </div>

      <button onClick={handleLogin}>Login with MOSIP</button>
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
}

export default Login;