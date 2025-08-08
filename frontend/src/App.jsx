import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import FileUpload from './components/FileUpload';
import Portfolios from './pages/Portfolios';
import PortfolioDetail from './pages/PortfolioDetail';
import Properties from './pages/Properties';
import PropertyDetail from './pages/PropertyDetail';
import Loans from './pages/Loans';
import LoanDetail from './pages/LoanDetail';

export default function App() {
  return (
    <div>
      <nav>
        <Link to="/upload">Upload</Link> |{' '}
        <Link to="/portfolios">Portfolios</Link> |{' '}
        <Link to="/properties">Properties</Link> |{' '}
        <Link to="/loans">Loans</Link>
      </nav>
      <Routes>
        <Route path="/upload" element={<FileUpload />} />
        <Route path="/portfolios" element={<Portfolios />} />
        <Route path="/portfolios/:id" element={<PortfolioDetail />} />
        <Route path="/properties" element={<Properties />} />
        <Route path="/properties/:id" element={<PropertyDetail />} />
        <Route path="/loans" element={<Loans />} />
        <Route path="/loans/:id" element={<LoanDetail />} />
      </Routes>
    </div>
  );
}
