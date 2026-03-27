import { Bell, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/auth/useAuth';

export function Header() {
  const { username, logout, isAuthenticated } = useAuth();

  return (
    <header className="h-16 border-b border-slate-200 bg-white px-6 flex items-center justify-between">
      <div className="text-sm text-slate-500">
        {isAuthenticated ? `Welcome back, ${username || 'Admin'}` : 'Skill-0 Dashboard'}
      </div>
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon">
          <Bell className="h-5 w-5 text-slate-500" />
        </Button>
        <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center">
          <User className="h-5 w-5 text-slate-500" />
        </div>
        {isAuthenticated && (
          <Button variant="outline" size="sm" onClick={logout}>
            Sign out
          </Button>
        )}
      </div>
    </header>
  );
}
