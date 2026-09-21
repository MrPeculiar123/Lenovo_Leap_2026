import { useEffect, useState } from 'react';
import AppShell from '../components/AppShell';
import Loading from '../components/Loading';
import { api } from '../services/api';
import { Empty } from './Dashboard';
import { BookOpen, CheckCircle2 } from 'lucide-react';

export default function LearningPlan() {
  const [data, setData] = useState(null); const [error, setError] = useState('');
  const load = () => { setError(''); api.getDashboard().then(setData).catch(e => setError(e.message)); };
  useEffect(load, []);
  if (!data && !error) return <AppShell><Loading message="Loading your learning plan..." /></AppShell>;
  if (error) return <AppShell><Empty title="Could not load your learning plan" text={error} action={load} /></AppShell>;
  const plan = data.study_plan || [];
  return <AppShell><p className="text-sm font-medium text-indigo-600">Personalized path</p><h1 className="mt-2 text-3xl font-bold">Learning plan</h1><p className="mt-2 max-w-2xl text-slate-500">{data.plan_summary || 'Your plan is based on your latest assessment and priority gaps.'}</p><div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6"><h2 className="flex items-center gap-2 font-bold"><BookOpen size={19} className="text-indigo-600" /> Recommended study steps</h2>{plan.length ? <div className="mt-5 space-y-3">{plan.map((item, index) => <div key={index} className="flex gap-3 rounded-xl bg-slate-50 p-4"><CheckCircle2 size={19} className="mt-0.5 shrink-0 text-indigo-500" /><div className="text-sm leading-6 text-slate-700">{typeof item === 'string' ? item : item.title || item.topic || item.description || JSON.stringify(item)}</div></div>)}</div> : <p className="mt-4 text-sm text-slate-500">Complete an assessment to generate your personalized study plan.</p>}</div></AppShell>;
}
