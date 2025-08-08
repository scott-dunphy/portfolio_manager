import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

export default function Properties() {
  const [data, setData] = useState([]);

  useEffect(() => {
    fetch('/api/properties').then(r => r.json()).then(setData);
  }, []);

  return (
    <div>
      <h2>Properties</h2>
      <ul>
        {data.map(p => (
          <li key={p.id}>
            <Link to={`/properties/${p.id}`}>{p.address}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
