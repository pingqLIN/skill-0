import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { SkillsList } from './pages/SkillsList';
import { ReviewQueue } from './pages/ReviewQueue';
import { AuditLog } from './pages/AuditLog';
import { SkillDetail } from './pages/SkillDetail';
import { GraphView } from './pages/GraphView';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/skills" element={<SkillsList />} />
          <Route path="/skills/:skillId" element={<SkillDetail />} />
          <Route path="/graph" element={<GraphView />} />
          <Route path="/review" element={<ReviewQueue />} />
          <Route path="/audit" element={<AuditLog />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
