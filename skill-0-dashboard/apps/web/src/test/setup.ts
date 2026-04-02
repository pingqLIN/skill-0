import '@testing-library/jest-dom';
import { AUTH_TOKEN_STORAGE_KEY } from '@/auth/storage';

beforeEach(() => {
  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, 'test-token');
});

afterEach(() => {
  window.localStorage.clear();
});
