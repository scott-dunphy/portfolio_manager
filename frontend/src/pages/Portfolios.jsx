import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

export default function Portfolios() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch('/api/portfolios').then(r => r.json()).then(setData);
  }, []);

  return (
    <div>
      <h2>Portfolios</h2>
      <ul>
        {data.map(p => (
          <li key={p.id}>
            <Link to={`/portfolios/${p.id}`}>{p.name}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
