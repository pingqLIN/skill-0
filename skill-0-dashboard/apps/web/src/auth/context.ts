import { createContext } from 'react';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthContextValue {
  status: AuthStatus;
  isAuthenticated: boolean;
  username: string | null;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

export const defaultAuthContext: AuthContextValue = {
  status: 'unauthenticated',
  isAuthenticated: false,
  username: null,
  login: async () => undefined,
  logout: () => undefined,
};

export const AuthContext = createContext<AuthContextValue>(defaultAuthContext);
