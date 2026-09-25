import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

import Landing from './pages/Landing';
import Login from './pages/Login';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import Assessment from './pages/Assessment';
import History from './pages/History';
import Tutor from './pages/Tutor';
import Progress from './pages/Progress';
import LearningPlan from './pages/LearningPlan';
import AssessmentResult from './pages/AssessmentResult';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />

          {/* Protected Routes */}
          <Route
            path="/onboarding"
            element={
              <ProtectedRoute>
                <Onboarding />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute requireOnboarding={true}>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/assessment" element={<ProtectedRoute requireOnboarding><Assessment /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute requireOnboarding><History /></ProtectedRoute>} />
          <Route path="/history/:assessmentId" element={<ProtectedRoute requireOnboarding><AssessmentResult /></ProtectedRoute>} />
          <Route path="/tutor" element={<ProtectedRoute requireOnboarding><Tutor /></ProtectedRoute>} />
          <Route path="/progress" element={<ProtectedRoute requireOnboarding><Progress /></ProtectedRoute>} />
          <Route path="/learning-plan" element={<ProtectedRoute requireOnboarding><LearningPlan /></ProtectedRoute>} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
