import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders login prompt', () => {
  render(<App />);
  const headingElement = screen.getByText(/login with your national id/i);
  expect(headingElement).toBeInTheDocument();
});
