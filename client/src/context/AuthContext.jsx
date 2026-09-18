import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('access_token'));
  const [onboardingProfile, setOnboardingProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize auth state on app load
  useEffect(() => {
    async function initAuth() {
      const storedToken = localStorage.getItem('access_token');
      if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        // Verify token & get current user
        const userData = await api.getCurrentUser();
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));

        // Fetch onboarding profile if it exists
        try {
          const profile = await api.getOnboardingProfile();
          setOnboardingProfile(profile);
        } catch (profileErr) {
          // If 404 or profile not set yet, onboardingProfile remains null
          setOnboardingProfile(null);
        }
      } catch (err) {
        // Invalid or expired token
        console.warn('Auth initialization failed, clearing token:', err.message);
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        setToken(null);
        setUser(null);
        setOnboardingProfile(null);
      } finally {
        setLoading(false);
      }
    }

    initAuth();
  }, []);

  const login = async (email, password) => {
    const data = await api.login(email, password);
    const { access_token, user: userData } = data;

    localStorage.setItem('access_token', access_token);
    localStorage.setItem('user', JSON.stringify(userData));
    setToken(access_token);
    setUser(userData);

    // Check existing onboarding profile
    let profile = null;
    try {
      profile = await api.getOnboardingProfile();
      setOnboardingProfile(profile);
    } catch {
      setOnboardingProfile(null);
    }

    return { user: userData, hasProfile: !!profile };
  };

  const register = async (email, password) => {
    const data = await api.register(email, password);
    const { access_token, user: userData } = data;

    localStorage.setItem('access_token', access_token);
    localStorage.setItem('user', JSON.stringify(userData));
    setToken(access_token);
    setUser(userData);
    setOnboardingProfile(null);

    return { user: userData };
  };

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    setOnboardingProfile(null);
  }, []);

  const completeOnboardingProfile = async (profileData) => {
    const profile = await api.completeOnboarding(profileData);
    setOnboardingProfile(profile);
    return profile;
  };

  const value = {
    user,
    token,
    onboardingProfile,
    isAuthenticated: !!token && !!user,
    loading,
    login,
    register,
    logout,
    completeOnboardingProfile,
    setOnboardingProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
