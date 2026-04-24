import React from 'react';
import { getUserType } from '../api';

const personalOffers = [
  { lender: 'Lesotho PostBank', product: 'Personal Loan', amount: 'M500 - M5,000', rate: '4-7%' },
  { lender: 'Letshego', product: 'School Fees Advance', amount: 'M1,000 - M10,000', rate: '5%' },
];

const businessOffers = [
  { lender: 'Lesotho PostBank', product: 'MSME Working Capital', amount: 'M5,000 - M20,000', rate: '5-8%' },
  { lender: 'Microfin', product: 'Stock Purchase Loan', amount: 'M500 - M5,000', rate: '6-10%' },
];

function Offers() {
  const userType = getUserType();
  const offers = userType === 'business' ? businessOffers : personalOffers;

  return (
    <div style={{ padding: 20, maxWidth: 500, margin: '0 auto' }}>
      <h1>{userType === 'business' ? 'Business Loan Offers' : 'Personal Loan Offers'}</h1>
      {offers.map((o, i) => (
        <div key={i} style={{ border: '1px solid #ccc', padding: 10, marginBottom: 10 }}>
          <strong>{o.lender}</strong> – {o.product}<br />
          Amount: {o.amount}<br />
          Interest: {o.rate}
        </div>
      ))}
    </div>
  );
}

export default Offers;