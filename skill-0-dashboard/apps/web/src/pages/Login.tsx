import { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Shield, LockKeyhole, LoaderCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/auth/useAuth';

export function LoginPage() {
  const location = useLocation();
  const { status, isAuthenticated, login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const redirectTo = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/';

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await login({ username, password });
    } catch (loginError) {
      const message =
        (loginError as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (loginError as Error).message ||
        'Login failed';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 px-4 py-10">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-5xl items-center justify-center">
        <div className="grid w-full gap-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-xl md:grid-cols-[1.2fr_0.8fr] md:p-8">
          <section className="rounded-2xl bg-slate-900 p-8 text-white">
            <div className="mb-8 inline-flex rounded-full bg-white/10 p-3">
              <Shield className="h-6 w-6" />
            </div>
            <h1 className="mb-3 text-3xl font-semibold">Skill-0 Governance Console</h1>
            <p className="max-w-lg text-sm leading-6 text-slate-300">
              Sign in with the main Skill-0 API credentials to review skills, inspect scan history,
              and run governance actions from the dashboard.
            </p>
            <div className="mt-10 grid gap-4 text-sm text-slate-300">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                JWTs are issued by the core API and reused by the dashboard API.
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                Session state is stored locally in this browser and cleared automatically after a
                `401`.
              </div>
            </div>
          </section>

          <Card className="border-slate-200 shadow-none">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                <LockKeyhole className="h-5 w-5" />
                Sign In
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleSubmit}>
                <label className="block space-y-2">
                  <span className="text-sm font-medium text-slate-700">Username</span>
                  <Input
                    autoComplete="username"
                    placeholder="admin"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    disabled={isSubmitting || status === 'loading'}
                  />
                </label>

                <label className="block space-y-2">
                  <span className="text-sm font-medium text-slate-700">Password</span>
                  <Input
                    type="password"
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    disabled={isSubmitting || status === 'loading'}
                  />
                </label>

                {error && (
                  <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    {error}
                  </div>
                )}

                <Button
                  type="submit"
                  className="w-full bg-slate-900 hover:bg-slate-800"
                  disabled={!username || !password || isSubmitting || status === 'loading'}
                >
                  {isSubmitting || status === 'loading' ? (
                    <>
                      <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                      Signing in...
                    </>
                  ) : (
                    'Access Dashboard'
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
