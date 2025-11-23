/**
 * Main App Component
 */
import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';

// Pages
import EnhancedLandingPage from './pages/EnhancedLandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import EnhancedOnboardingPage from './pages/EnhancedOnboardingPage';
import DashboardPage from './pages/DashboardPage';
import MatchesPage from './pages/MatchesPage';
import AIConversationPage from './pages/AIConversationPage';
import RealTimeConversationPage from './pages/RealTimeConversationPage';

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

function App() {
  const initialize = useAuthStore((state) => state.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-calm-50 via-white to-primary-50">
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<EnhancedLandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected Routes */}
        <Route
          path="/onboarding"
          element={
            <ProtectedRoute>
              <EnhancedOnboardingPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/matches"
          element={
            <ProtectedRoute>
              <MatchesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/ai-conversation/:matchId"
          element={
            <ProtectedRoute>
              <AIConversationPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/live-conversation/:matchId"
          element={
            <ProtectedRoute>
              <RealTimeConversationPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  );
}

export default App;
