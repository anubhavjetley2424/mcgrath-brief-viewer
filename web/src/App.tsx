import { HashRouter, Routes, Route } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Kanban from './pages/Kanban';
import DealDetail from './pages/DealDetail';
import Drafts from './pages/Drafts';
import Activities from './pages/Activities';
import MapDashboard from './pages/MapDashboard';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <Routes>
          {/* Map is standalone so it can be embedded cleanly in Airtable or run full-screen on GitHub Pages */}
          <Route path="/map" element={<MapDashboard />} />
          
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/deals" element={<Kanban />} />
            <Route path="/deals/:id" element={<DealDetail />} />
            <Route path="/drafts" element={<Drafts />} />
            <Route path="/activities" element={<Activities />} />
          </Route>
        </Routes>
      </HashRouter>
    </QueryClientProvider>
  );
}
