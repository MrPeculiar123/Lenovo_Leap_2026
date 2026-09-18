const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/**
 * Custom error class for API errors with status code and detail message.
 */
export class ApiError extends Error {
  constructor(message, status, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Core fetch wrapper with auth header and error handling.
 */
async function request(endpoint, options = {}) {
  const token = localStorage.getItem('access_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
  };

  let response;
  try {
    response = await fetch(`${API_URL}${endpoint}`, config);
  } catch (err) {
    throw new ApiError('Unable to connect to server. Please check if the backend is running.', 0);
  }

  let data = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    let message = 'An unexpected error occurred.';
    const detail = data?.detail;

    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail) && detail[0]?.msg) {
      message = detail[0].msg;
    } else {
      switch (response.status) {
        case 400:
          message = 'Bad request. Please check your input.';
          break;
        case 401:
          message = 'Invalid credentials or expired session.';
          break;
        case 404:
          message = 'Resource not found.';
          break;
        case 409:
          message = 'This email is already registered.';
          break;
        case 422:
          message = 'Invalid data provided.';
          break;
        case 500:
          message = 'Internal server error. Please try again later.';
          break;
        default:
          message = `Request failed with status ${response.status}`;
      }
    }

    throw new ApiError(message, response.status, detail);
  }

  return data;
}

export const api = {
  // Auth endpoints
  async register(email, password) {
    return request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async login(email, password) {
    return request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async getCurrentUser() {
    return request('/auth/me', {
      method: 'GET',
    });
  },

  // Onboarding endpoints
  async completeOnboarding(profileData) {
    return request('/onboarding/complete', {
      method: 'POST',
      body: JSON.stringify(profileData),
    });
  },

  async getOnboardingProfile() {
    return request('/onboarding/me', {
      method: 'GET',
    });
  },
};
