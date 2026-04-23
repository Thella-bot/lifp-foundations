import React, { useEffect, useState } from 'react';
import { getScore } from '../api';
import { useNavigate } from 'react-router-dom';
import GaugeChart from 'react-gauge-chart'; // or implement a custom one
// We'll avoid extra dependencies; use a simple div styled.

function Dashboard() {
  const [scoreData, setScoreData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    getScore().then(setScoreData).catch(() => navigate('/'));
  }, [navigate]);

  if (!scoreData) return <div>Loading...</div>;

  const { score, tier, prob_default } = scoreData;

  const tierColors = { A: '#00cc44', B: '#33cc33', C: '#cccc00', D: '#ff9900', E: '#ff3333' };
  const color = tierColors[tier] || '#bbb';

  return (
    <div style={{ padding: 20 }}>
      <h1>LIFP Dashboard</h1>
      <div style={{ textAlign: 'center', margin: '30px 0' }}>
        <div style={{ fontSize: 60, color }}>{score}</div>
        <div>Credit Score</div>
        <div>Risk Tier: <strong>{tier}</strong></div>
        <div>Default Probability: {(prob_default*100).toFixed(1)}%</div>
      </div>
      <button onClick={() => navigate('/record')}>Record Transaction</button>
      <button onClick={() => navigate('/offers')}>View Loan Offers</button>
      <button onClick={() => navigate('/learn')}>Learn</button>
    </div>
  );
}
export default Dashboard;