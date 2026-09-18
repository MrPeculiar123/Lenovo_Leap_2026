import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Loading from './Loading';

export function ProtectedRoute({ children, requireOnboarding = false }) {
  const { isAuthenticated, loading, onboardingProfile } = useAuth();
  const location = useLocation();

  if (loading) {
    return <Loading fullScreen message="Verifying session..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If page requires onboarding completed (e.g. dashboard) but user has no profile
  if (requireOnboarding && !onboardingProfile) {
    return <Navigate to="/onboarding" replace />;
  }

  return children;
}

export default ProtectedRoute;
