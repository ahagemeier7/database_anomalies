import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from '../components/Layout';
import WorkersPage from '../pages/Dashboard';
import RevisionsPage from '../pages/RevisionsPage';

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        {/* A rota pai carrega o Menu. As filhas entram no <Outlet /> */}
        <Route element={<Layout />}>
          
          <Route path="/" element={<WorkersPage />} />
          
          <Route path="/revisions" element={<RevisionsPage />} />
          <Route path="/revisions/:tableName" element={<RevisionsPage />} />
          
          {/* Rota 404 de fallback */}
          <Route path="*" element={<h2>Página não encontrada 🛑</h2>} />
          
        </Route>
      </Routes>
    </BrowserRouter>
  );
}