import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { FileQuestion } from 'lucide-react';
import { Layout } from '../components/Layout';
import WorkersPage from '../pages/WorkersPage';
import RevisionsPage from '../pages/RevisionsPage';
import StatsPage from '../pages/StatsPage';
import { EmptyState } from '../components/ui';

export default function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        {/* A rota pai carrega o Menu. As filhas entram no <Outlet /> */}
        <Route element={<Layout />}>

          <Route path="/" element={<WorkersPage />} />

          <Route path="/revisions" element={<RevisionsPage />} />
          <Route path="/revisions/:tableName" element={<RevisionsPage />} />
          <Route path="/stats" element={<StatsPage />} />

          {/* Rota 404 de fallback */}
          <Route path="*" element={
            <EmptyState
              icon={FileQuestion}
              title="Page not found"
              description="The page you are looking for doesn't exist."
            />
          } />

        </Route>
      </Routes>
    </BrowserRouter>
  );
}