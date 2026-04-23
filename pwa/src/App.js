import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import RecordTransaction from './pages/RecordTransaction';
import Offers from './pages/Offers';
import Learn from './pages/Learn';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/record" element={<RecordTransaction />} />
        <Route path="/offers" element={<Offers />} />
        <Route path="/learn" element={<Learn />} />
      </Routes>
    </Router>
  );
}
export default App;