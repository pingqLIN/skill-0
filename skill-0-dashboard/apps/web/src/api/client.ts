import axios from 'axios';
import { clearStoredAuthToken, getStoredAuthToken } from '@/auth/storage';

const dashboardApiBaseUrl =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? 'http://localhost:8001' : '/dashboard-api');

const coreApiBaseUrl =
  import.meta.env.VITE_CORE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

export const api = axios.create({
  baseURL: dashboardApiBaseUrl,
});

export const authApi = axios.create({
  baseURL: coreApiBaseUrl,
});

api.interceptors.request.use((config) => {
  const token = getStoredAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearStoredAuthToken();
    }
    return Promise.reject(error);
  }
);
