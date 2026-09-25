const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, status, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request(endpoint, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const token = localStorage.getItem('access_token');
  if (token) headers.Authorization = `Bearer ${token}`;
  let response;
  try {
    response = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
  } catch {
    throw new ApiError('Unable to connect to the server.', 0);
  }
  let data = null;
  if (response.headers.get('content-type')?.includes('application/json')) data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg : `Request failed (${response.status})`;
    throw new ApiError(message || 'Something went wrong.', response.status, detail);
  }
  return data;
}

export const api = {
  register: (email, password) => request('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  login: (email, password) => request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  getCurrentUser: () => request('/auth/me'),
  completeOnboarding: (profileData) => request('/onboarding/complete', { method: 'POST', body: JSON.stringify(profileData) }),
  getOnboardingProfile: () => request('/onboarding/me'),
  startAssessment: (payload = {}) => request('/navigator/start-assessment', { method: 'POST', body: JSON.stringify(payload) }),
  submitAnswer: (payload) => request('/navigator/submit-answer', { method: 'POST', body: JSON.stringify(payload) }),
  getDashboard: () => request('/navigator/dashboard-data'),
  getAssessmentHistory: () => request('/navigator/assessment-history'),
  getAssessmentDetail: (assessmentId) => request(`/navigator/assessment/${assessmentId}`),
  updatePlanProgress: (day, completion_status) => request('/navigator/learning-plan/progress', { method: 'PATCH', body: JSON.stringify({ day, completion_status }) }),
  analyzeAndPlan: (payload = {}) => request('/navigator/analyze-and-plan', { method: 'POST', body: JSON.stringify(payload) }),
  tutorChat: (message, language) => request('/navigator/tutor/chat', { method: 'POST', body: JSON.stringify({ message, language }) }),
};
