import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

export default function PropertyDetail() {
  const { id } = useParams();
  const [property, setProperty] = useState(null);
  const [status, setStatus] = useState('');

  useEffect(() => {
    fetch(`/api/properties/${id}`).then(r => r.json()).then(setProperty);
  }, [id]);

  const handleChange = e => {
    setProperty({ ...property, [e.target.name]: e.target.value });
  };

  const handleSubmit = async e => {
    e.preventDefault();
    try {
      const res = await fetch(`/api/properties/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...property,
          value: parseFloat(property.value)
        })
      });
      if (!res.ok) throw new Error('Save failed');
      setStatus('Saved');
    } catch (err) {
      setStatus(err.message);
    }
  };

  if (!property) return <p>Loading...</p>;
  return (
    <form onSubmit={handleSubmit}>
      <label>
        Address
        <input name="address" value={property.address || ''} onChange={handleChange} required />
      </label>
      <label>
        Value
        <input name="value" type="number" step="0.01" value={property.value || ''} onChange={handleChange} required />
      </label>
      <button type="submit">Save</button>
      {status && <p>{status}</p>}
    </form>
  );
}
