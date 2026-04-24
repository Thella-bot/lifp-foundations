import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUserType } from '../api';

function RecordTransaction() {
  const [type, setType] = useState('income');
  const [amount, setAmount] = useState('');
  const navigate = useNavigate();
  const userType = getUserType();

  const handleSave = () => {
    const numericAmount = Number(amount);
    if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
      alert('Please enter a valid amount greater than 0.');
      return;
    }
    alert(`Saved ${userType} ${type} of M${amount}`);
    navigate('/dashboard');
  };

  const categories = userType === 'business'
    ? ['Sales', 'Service', 'Stock Purchase', 'Rent', 'Transport', 'Airtime', 'Electricity', 'Other']
    : ['Salary', 'Gift', 'Airtime', 'Electricity', 'Groceries', 'Transport', 'Other'];

  const [category, setCategory] = useState(categories[0]);

  return (
    <div style={{ padding: 20, maxWidth: 400, margin: '0 auto' }}>
      <h1>{userType === 'business' ? 'Business Transaction' : 'Personal Transaction'}</h1>
      <select value={type} onChange={e => setType(e.target.value)}>
        <option value="income">Income</option>
        <option value="expense">Expense</option>
      </select>
      <select value={category} onChange={e => setCategory(e.target.value)}>
        {categories.map(c => <option key={c} value={c}>{c}</option>)}
      </select>
      <input
        type="number"
        placeholder="Amount (M)"
        value={amount}
        onChange={e => setAmount(e.target.value)}
      />
      <button onClick={handleSave}>Save</button>
    </div>
  );
}

export default RecordTransaction;
