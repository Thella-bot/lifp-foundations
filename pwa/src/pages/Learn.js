import React from 'react';

const articles = [
  "Why separate business and personal money?",
  "How a credit score is calculated",
  "Tips to improve your credit score",
];

function Learn() {
  return (
    <div style={{ padding: 20, maxWidth: 500, margin: '0 auto' }}>
      <h1>Financial Literacy</h1>
      <ul>
        {articles.map((a, i) => <li key={i}>{a}</li>)}
      </ul>
    </div>
  );
}

export default Learn;