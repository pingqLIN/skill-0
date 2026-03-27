import { lazy, Suspense } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider } from '@/auth/AuthProvider';
import { useAuth } from '@/auth/useAuth';
import { LoginPage } from '@/pages/Login';

const Dashboard = lazy(() =>
  import('./pages/Dashboard').then((module) => ({ default: module.Dashboard }))
);
const SkillsList = lazy(() =>
  import('./pages/SkillsList').then((module) => ({ default: module.SkillsList }))
);
const ReviewQueue = lazy(() =>
  import('./pages/ReviewQueue').then((module) => ({ default: module.ReviewQueue }))
);
const AuditLog = lazy(() =>
  import('./pages/AuditLog').then((module) => ({ default: module.AuditLog }))
);
const SkillDetail = lazy(() =>
  import('./pages/SkillDetail').then((module) => ({ default: module.SkillDetail }))
);
const Security = lazy(() =>
  import('./pages/Security').then((module) => ({ default: module.Security }))
);

const queryClient = new QueryClient();

function RouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div
        className="h-8 w-8 animate-spin rounded-full border-b-2 border-slate-900"
        aria-label="Loading page"
      />
    </div>
  );
}

function ProtectedRoutes() {
  const { status, isAuthenticated } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <RouteFallback />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/skills" element={<SkillsList />} />
        <Route path="/skills/:skillId" element={<SkillDetail />} />
        <Route path="/review" element={<ReviewQueue />} />
        <Route path="/security" element={<Security />} />
        <Route path="/audit" element={<AuditLog />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="*" element={<ProtectedRoutes />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
