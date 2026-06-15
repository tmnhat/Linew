import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Overview from './pages/Overview';
import Sources from './pages/Sources';
import Pipeline from './pages/Pipeline';
import Governance from './pages/Governance';
import Settings from './pages/Settings';
import Logs from './pages/Logs';
import Distribution from './pages/Distribution';
import Newsletter from './pages/Newsletter';
import SEO from './pages/SEO';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  // Initialize WebSocket connection
  useWebSocket();

  return (
    <ErrorBoundary>
      <BrowserRouter basename="/dashboard">
        <Routes>
          {/* Login route - public */}
          <Route path="/login" element={<Login />} />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/overview" replace />} />
            <Route path="overview" element={<Overview />} />
            <Route path="sources" element={<Sources />} />
            <Route path="pipeline" element={<Pipeline />} />
            <Route path="governance" element={<Governance />} />
            <Route path="settings" element={<Settings />} />
            <Route path="logs" element={<Logs />} />
            <Route path="distribution" element={<Distribution />} />
            <Route path="newsletter" element={<Newsletter />} />
            <Route path="seo" element={<SEO />} />
          </Route>

          {/* Fallback redirect to overview */}
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
