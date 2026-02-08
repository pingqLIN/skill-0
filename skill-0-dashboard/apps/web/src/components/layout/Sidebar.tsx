import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, List, CheckCircle, Shield, FileText, Share2 } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/graph', label: 'Skill Graph', icon: Share2 },
  { path: '/skills', label: 'Skills', icon: List },
  { path: '/review', label: 'Review Queue', icon: CheckCircle },
  { path: '/security', label: 'Security', icon: Shield },
  { path: '/audit', label: 'Audit Log', icon: FileText },
];

export function Sidebar() {
  const location = useLocation();
  
  return (
    <aside className="w-64 bg-white border-r border-slate-200 p-4">
      <div className="text-xl font-bold mb-8">Skill-0</div>
      <nav className="space-y-2">
        {navItems.map(({ path, label, icon: Icon }) => (
          <Link
            key={path}
            to={path}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              location.pathname === path
                ? 'bg-slate-100 text-slate-900'
                : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Icon className="h-5 w-5" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
