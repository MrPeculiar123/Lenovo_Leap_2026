import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, ClipboardCheck, TrendingUp, BookOpen, MessageCircle, History, Menu, X, LogOut, Compass } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const links = [
  ['/dashboard', 'Overview', LayoutDashboard],
  ['/assessment', 'Assessment', ClipboardCheck],
  ['/progress', 'Progress', TrendingUp],
  ['/learning-plan', 'Learning plan', BookOpen],
  ['/tutor', 'AI tutor', MessageCircle],
  ['/history', 'History', History],
];

export default function AppShell({ children }) {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const signOut = () => { logout(); navigate('/login'); };
  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-200 bg-white transition-transform lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex h-20 items-center justify-between px-6">
          <NavLink to="/dashboard" className="flex items-center gap-2 text-lg font-bold tracking-tight"><span className="rounded-xl bg-indigo-600 p-2 text-white"><Compass size={18} /></span>PathForge</NavLink>
          <button className="lg:hidden" onClick={() => setOpen(false)}><X size={20} /></button>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          <p className="px-3 pb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Workspace</p>
          {links.map(([to, label, Icon]) => <NavLink key={to} to={to} onClick={() => setOpen(false)} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'}`}><Icon size={18} />{label}</NavLink>)}
        </nav>
        <div className="border-t border-slate-100 p-4">
          <div className="mb-3 flex items-center gap-3 rounded-xl bg-slate-50 p-3"><div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">{user?.email?.[0]?.toUpperCase() || 'U'}</div><span className="truncate text-xs font-medium text-slate-700">{user?.email}</span></div>
          <button onClick={signOut} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-rose-50 hover:text-rose-600"><LogOut size={16} />Sign out</button>
        </div>
      </aside>
      {open && <button aria-label="Close menu" className="fixed inset-0 z-30 bg-slate-900/20 lg:hidden" onClick={() => setOpen(false)} />}
      <main className="min-h-screen lg:pl-64"><header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:px-8"><button className="rounded-lg p-2 hover:bg-slate-100 lg:hidden" onClick={() => setOpen(true)}><Menu size={21} /></button><div className="ml-auto text-sm text-slate-500">Welcome back, <span className="font-semibold text-slate-800">{user?.email?.split('@')[0]}</span></div></header><div className="mx-auto max-w-7xl p-4 sm:p-6 lg:p-8">{children}</div></main>
    </div>
  );
}
