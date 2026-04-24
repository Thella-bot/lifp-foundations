import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getScore, getUserType } from '../api';

function Dashboard() {
  const [scoreData, setScoreData] = useState(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const userType = getUserType();

  useEffect(() => {
    getScore()
      .then(setScoreData)
      .catch((e) => setError(e.message || 'Failed to load score'));
  }, [navigate]);

  if (error) {
    return (
      <div style={{ padding: 20, maxWidth: 500, margin: '0 auto', textAlign: 'center' }}>
        <h1>Unable to load dashboard</h1>
        <p>{error}</p>
        <button onClick={() => navigate('/')}>Back to login</button>
      </div>
    );
  }

  if (!scoreData) return <div>Loading...</div>;

  const { score, tier, prob_default } = scoreData;
  const tierColors = {
    A: '#2e7d32', B: '#4caf50', C: '#fbc02d', D: '#f57c00', E: '#c62828'
  };
  const color = tierColors[tier] || '#888';

  return (
    <div style={{ padding: 20, maxWidth: 500, margin: '0 auto', textAlign: 'center' }}>
      <h1>{userType === 'business' ? 'Business Dashboard' : 'Personal Dashboard'}</h1>
      <div style={{ fontSize: 72, fontWeight: 'bold', color }}>{score}</div>
      <p>Credit Score</p>
      <div style={{ display: 'flex', justifyContent: 'space-around', margin: '20px 0' }}>
        <div><strong>Tier</strong><br />{tier}</div>
        <div><strong>Default Risk</strong><br />{(prob_default * 100).toFixed(1)}%</div>
      </div>

      {/* Different quick stats for individuals vs businesses */}
      {userType === 'business' ? (
        <div style={{ textAlign: 'left', margin: '20px 0' }}>
          <p><strong>Total Merchant Payments:</strong> M4,500 (demo)</p>
          <p><strong>Inventory Value:</strong> M12,300 (demo)</p>
        </div>
      ) : (
        <div style={{ textAlign: 'left', margin: '20px 0' }}>
          <p><strong>Monthly Airtime Spend:</strong> M120 (demo)</p>
          <p><strong>Recurring Bill Payments:</strong> 3 active</p>
        </div>
      )}

      <div>
        <button onClick={() => navigate('/record')}>
          {userType === 'business' ? 'Record Business Transaction' : 'Record Transaction'}
        </button>
        <button onClick={() => navigate('/offers')}>
          {userType === 'business' ? 'Business Loan Offers' : 'Personal Loan Offers'}
        </button>
        <button onClick={() => navigate('/learn')}>Learn</button>
      </div>
    </div>
  );
}

export default Dashboard;
