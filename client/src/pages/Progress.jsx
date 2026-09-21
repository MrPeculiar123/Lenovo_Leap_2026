import { useEffect, useState } from 'react';
import AppShell from '../components/AppShell';
import Loading from '../components/Loading';
import { api } from '../services/api';
import { Empty } from './Dashboard';
import { TrendingUp } from 'lucide-react';

export default function Progress() {
  const [data, setData] = useState(null); const [error, setError] = useState('');
  const load = () => { setError(''); api.getDashboard().then(setData).catch(e => setError(e.message)); };
  useEffect(load, []);
  if (!data && !error) return <AppShell><Loading message="Loading your progress..." /></AppShell>;
  if (error) return <AppShell><Empty title="Could not load progress" text={error} action={load} /></AppShell>;
  const mastery = Object.entries(data.concept_mastery || {});
  return <AppShell><p className="text-sm font-medium text-indigo-600">Your growth</p><h1 className="mt-2 text-3xl font-bold">Progress</h1><p className="mt-2 text-slate-500">A snapshot of the concepts and domains in your latest profile.</p><div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6"><h2 className="flex items-center gap-2 font-bold"><TrendingUp size={19} className="text-indigo-600" /> Concept mastery</h2>{mastery.length ? <div className="mt-5 grid gap-4 sm:grid-cols-2">{mastery.map(([name, value]) => { const score = Math.min(100, value <= 1 ? value * 100 : value); return <div key={name} className="rounded-xl bg-slate-50 p-4"><div className="flex justify-between gap-3 text-sm"><span className="font-medium text-slate-700">{name}</span><span className="font-semibold text-indigo-700">{Math.round(score)}%</span></div><div className="mt-3 h-2 rounded-full bg-white"><div className="h-2 rounded-full bg-indigo-500" style={{ width: `${score}%` }} /></div></div>; })}</div> : <p className="mt-4 text-sm text-slate-500">Complete an assessment to see concept mastery.</p>}</div></AppShell>;
}
