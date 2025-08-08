import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

export default function Loans() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch('/api/loans').then(r => r.json()).then(setData);
  }, []);

  return (
    <div>
      <h2>Loans</h2>
      <ul>
        {data.map(l => (
          <li key={l.id}>
            <Link to={`/loans/${l.id}`}>{l.amount}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
