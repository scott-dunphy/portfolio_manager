import React, { useState } from 'react';

export default function FileUpload() {
  const [status, setStatus] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    setStatus('Uploading...');
    try {
      const res = await fetch('/upload', {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error('Upload failed');
      setStatus('Upload successful');
    } catch (err) {
      setStatus(err.message);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input type="file" name="file" required />
      <button type="submit">Upload</button>
      {status && <p>{status}</p>}
    </form>
  );
}
