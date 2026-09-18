import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Navbar from '../components/Navbar';
import Button from '../components/Button';
import Input from '../components/Input';
import { Mail, Lock, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react';

export function Login() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login, register, isAuthenticated, onboardingProfile, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // If already logged in, redirect away from login page
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      if (onboardingProfile) {
        navigate('/dashboard', { replace: true });
      } else {
        navigate('/onboarding', { replace: true });
      }
    }
  }, [isAuthenticated, onboardingProfile, authLoading, navigate]);

  const validateForm = () => {
    const errors = {};
    setError('');

    if (!email || !email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = 'Please enter a valid email address';
    }

    if (!password) {
      errors.password = 'Password is required';
    } else if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters long';
    }

    if (isRegister) {
      if (!confirmPassword) {
        errors.confirmPassword = 'Please confirm your password';
      } else if (password !== confirmPassword) {
        errors.confirmPassword = 'Passwords do not match';
      }
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);
    setError('');

    try {
      if (isRegister) {
        await register(email, password);
        // After registration, user needs to complete onboarding
        navigate('/onboarding', { replace: true });
      } else {
        const { hasProfile } = await login(email, password);
        if (hasProfile) {
          navigate('/dashboard', { replace: true });
        } else {
          navigate('/onboarding', { replace: true });
        }
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleTab = (registerMode) => {
    setIsRegister(registerMode);
    setError('');
    setFieldErrors({});
    setEmail('');
    setPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />

      <div className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-8 relative overflow-hidden">
        {/* Glow backdrop */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-600/15 blur-[120px] rounded-full pointer-events-none" />

        <div className="w-full max-w-md relative z-10">
          {/* Main Card */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-2xl p-6 sm:p-8 backdrop-blur-xl">
            {/* Header */}
            <div className="text-center mb-6">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-3">
                <Sparkles className="w-6 h-6" />
              </div>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                {isRegister ? 'Create an Account' : 'Welcome Back'}
              </h1>
              <p className="text-sm text-slate-400 mt-1">
                {isRegister
                  ? 'Start your personalized AI learning journey'
                  : 'Sign in to access your skills & roadmap'}
              </p>
            </div>

            {/* Toggle Tabs */}
            <div className="grid grid-cols-2 p-1 bg-slate-950 rounded-xl border border-slate-800/80 mb-6">
              <button
                type="button"
                onClick={() => toggleTab(false)}
                className={`py-2 text-xs font-semibold rounded-lg transition-all ${
                  !isRegister
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => toggleTab(true)}
                className={`py-2 text-xs font-semibold rounded-lg transition-all ${
                  isRegister
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Register
              </button>
            </div>

            {/* Global Error Banner */}
            {error && (
              <div className="mb-6 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start space-x-2.5">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}

            {/* Auth Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                id="auth-email"
                label="Email Address"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                icon={Mail}
                error={fieldErrors.email}
                required
              />

              <Input
                id="auth-password"
                label="Password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                icon={Lock}
                error={fieldErrors.password}
                helperText={isRegister ? 'Must be at least 8 characters' : undefined}
                required
              />

              {isRegister && (
                <Input
                  id="auth-confirm-password"
                  label="Confirm Password"
                  type="password"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  icon={Lock}
                  error={fieldErrors.confirmPassword}
                  required
                />
              )}

              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  className="w-full"
                  isLoading={isSubmitting}
                >
                  {isRegister ? 'Create Account' : 'Sign In'}
                </Button>
              </div>
            </form>

            {/* Footer switcher text */}
            <div className="mt-6 text-center text-xs text-slate-400">
              {isRegister ? (
                <p>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => toggleTab(false)}
                    className="text-indigo-400 font-semibold hover:underline"
                  >
                    Sign In
                  </button>
                </p>
              ) : (
                <p>
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={() => toggleTab(true)}
                    className="text-indigo-400 font-semibold hover:underline"
                  >
                    Create Account
                  </button>
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
