import {
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { authApi } from '@/api/client';
import {
  AUTH_TOKEN_CLEARED_EVENT,
  clearStoredAuthToken,
  getStoredAuthToken,
  storeAuthToken,
} from './storage';
import { AuthContext, type AuthContextValue, type AuthStatus } from './context';

async function fetchCurrentUser(token: string) {
  const { data } = await authApi.get('/api/auth/me', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return data as { username?: string };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>(() =>
    getStoredAuthToken() ? 'loading' : 'unauthenticated'
  );
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    const token = getStoredAuthToken();
    if (!token) {
      return;
    }

    let active = true;

    fetchCurrentUser(token)
      .then((user) => {
        if (!active) {
          return;
        }
        setUsername(user.username ?? null);
        setStatus('authenticated');
      })
      .catch(() => {
        if (!active) {
          return;
        }
        clearStoredAuthToken();
        setUsername(null);
        setStatus('unauthenticated');
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const handleCleared = () => {
      setUsername(null);
      setStatus('unauthenticated');
    };

    window.addEventListener(AUTH_TOKEN_CLEARED_EVENT, handleCleared);
    return () => {
      window.removeEventListener(AUTH_TOKEN_CLEARED_EVENT, handleCleared);
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      isAuthenticated: status === 'authenticated',
      username,
      async login({ username: submittedUsername, password }) {
        const { data } = await authApi.post('/api/auth/token', {
          username: submittedUsername,
          password,
        });

        const token = data.access_token as string | undefined;
        if (!token) {
          throw new Error('Auth server did not return an access token.');
        }

        storeAuthToken(token);

        try {
          const currentUser = await fetchCurrentUser(token);
          setUsername(currentUser.username ?? submittedUsername);
        } catch {
          setUsername(submittedUsername);
        }

        setStatus('authenticated');
      },
      logout() {
        clearStoredAuthToken();
        setUsername(null);
        setStatus('unauthenticated');
      },
    }),
    [status, username]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
