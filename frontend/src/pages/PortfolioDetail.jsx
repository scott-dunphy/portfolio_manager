import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

export default function PortfolioDetail() {
  const { id } = useParams();
  const [portfolio, setPortfolio] = useState(null);
  const [status, setStatus] = useState('');

  useEffect(() => {
    fetch(`/api/portfolios/${id}`).then(r => r.json()).then(setPortfolio);
  }, [id]);

  const handleChange = e => {
    setPortfolio({ ...portfolio, [e.target.name]: e.target.value });
  };

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      const res = await fetch(`/api/portfolios/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(portfolio),
      });
      if (!res.ok) throw new Error('Save failed');
      setStatus('Saved');
    } catch (err) {
      setStatus(err.message);
    }
  };

  if (!portfolio) return <p>Loading...</p>;
  return (
    <form onSubmit={handleSubmit}>
      <label>
        Name
        <input name="name" value={portfolio.name || ''} onChange={handleChange} required />
      </label>
      <button type="submit">Save</button>
      {status && <p>{status}</p>}
    </form>
  );
}
