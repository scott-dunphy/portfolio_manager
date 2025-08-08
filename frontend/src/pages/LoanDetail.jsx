import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

export default function LoanDetail() {
  const { id } = useParams();
  const [loan, setLoan] = useState(null);
  const [status, setStatus] = useState('');

  useEffect(() => {
    fetch(`/api/loans/${id}`).then(r => r.json()).then(setLoan);
  }, [id]);

  const handleChange = e => {
    setLoan({ ...loan, [e.target.name]: e.target.value });
  };

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      const res = await fetch(`/api/loans/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...loan,
          amount: parseFloat(loan.amount),
          rate: parseFloat(loan.rate)
        })
      });
      if (!res.ok) throw new Error('Save failed');
      setStatus('Saved');
    } catch (err) {
      setStatus(err.message);
    }
  };

  if (!loan) return <p>Loading...</p>;
  return (
    <form onSubmit={handleSubmit}>
      <label>
        Amount
        <input name="amount" type="number" step="0.01" value={loan.amount || ''} onChange={handleChange} required />
      </label>
      <label>
        Rate
        <input name="rate" type="number" step="0.01" value={loan.rate || ''} onChange={handleChange} required />
      </label>
      <button type="submit">Save</button>
      {status && <p>{status}</p>}
    </form>
  );
}
