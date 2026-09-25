import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Compass, LogOut, User, Sparkles } from 'lucide-react';

export function Navbar() {
  const { user, isAuthenticated, logout, onboardingProfile } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-slate-950/80 border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform duration-200">
              <Compass className="w-6 h-6 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-lg text-white tracking-tight flex items-center gap-1.5">
                PathForge
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  AI
                </span>
              </span>
              <span className="text-xs text-slate-400 -mt-1 hidden sm:inline">Career & Skill Navigation</span>
            </div>
          </Link>

          {/* Right Navigation */}
          <div className="flex items-center space-x-4">
            {isAuthenticated ? (
              <>
                <div className="hidden md:flex items-center space-x-3">
                  <Link
                    to={onboardingProfile ? "/dashboard" : "/onboarding"}
                    className="text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition"
                  >
                    {onboardingProfile ? "Dashboard" : "Complete Setup"}
                  </Link>
                </div>

                <div className="flex items-center space-x-3 bg-slate-900/90 border border-slate-800/90 px-3 py-1.5 rounded-xl">
                  <div className="w-7 h-7 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center font-medium text-xs border border-indigo-500/30">
                    <User className="w-4 h-4" />
                  </div>
                  <span className="text-sm font-medium text-slate-200 max-w-[140px] sm:max-w-[200px] truncate">
                    {user?.email}
                  </span>
                </div>

                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-1.5 text-xs font-medium px-3 py-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all duration-200"
                  title="Sign Out"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="hidden sm:inline">Sign Out</span>
                </button>
              </>
            ) : (
              <div className="flex items-center space-x-3">
                <Link
                  to="/login"
                  className="text-sm font-medium text-slate-300 hover:text-white px-3 py-2 transition"
                >
                  Sign In
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center justify-center text-sm font-medium px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
                >
                  <Sparkles className="w-4 h-4 mr-1.5" />
                  Get Started
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
