import { useEffect, useState } from 'react';
import AppShell from '../components/AppShell';
import Loading from '../components/Loading';
import { api } from '../services/api';
import { Empty } from './Dashboard';
import ResourceList from '../components/ResourceList';
import { BookOpen, CheckCircle2, Circle } from 'lucide-react';

export default function LearningPlan() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [savingDay, setSavingDay] = useState(null);

  const load = () => { setError(''); api.getDashboard().then(setData).catch(err => setError(err.message)); };
  useEffect(load, []);

  const toggleDay = async day => {
    const current = data.plan_progress?.[String(day)] || 'pending';
    const completion_status = current === 'completed' ? 'pending' : 'completed';
    setSavingDay(day);
    try {
      await api.updatePlanProgress(day, completion_status);
      setData(currentData => ({ ...currentData, plan_progress: { ...(currentData.plan_progress || {}), [day]: completion_status }, study_plan: currentData.study_plan.map(item => item.day === day ? { ...item, completion_status } : item) }));
    } catch (err) { setError(err.message); } finally { setSavingDay(null); }
  };

  if (!data && !error) return <AppShell><Loading message="Loading your learning plan..." /></AppShell>;
  if (error && !data) return <AppShell><Empty title="Could not load your learning plan" text={error} action={load} /></AppShell>;
  const plan = data.study_plan || [];
  const resources = [...(data.grounded_resources || []), ...plan.flatMap(item => item.recommended_resources || [])].filter((resource, index, all) => resource?.id && all.findIndex(candidate => candidate.id === resource.id) === index);
  return <AppShell><p className="text-sm font-medium text-indigo-600">Personalized path</p><h1 className="mt-2 text-3xl font-bold">Learning plan</h1><p className="mt-2 max-w-2xl text-slate-500">{data.plan_summary || 'Your plan is based on your latest assessment and priority gaps.'}</p>{error && <p className="mt-5 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}<div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6"><h2 className="flex items-center gap-2 font-bold"><BookOpen size={19} className="text-indigo-600" /> Seven-day roadmap</h2>{plan.length ? <div className="mt-5 space-y-4">{plan.map(item => { const completed = (data.plan_progress?.[String(item.day)] || item.completion_status) === 'completed'; return <article key={item.day} className="rounded-xl bg-slate-50 p-5"><div className="flex items-start gap-3"><button type="button" disabled={savingDay === item.day} onClick={() => toggleDay(item.day)} className="mt-0.5 shrink-0 text-indigo-600" aria-label={`Mark day ${item.day} ${completed ? 'pending' : 'completed'}`}>{completed ? <CheckCircle2 size={21} /> : <Circle size={21} />}</button><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold">Day {item.day}: {item.focus_topic}</h3><span className="text-xs text-slate-500">{item.duration_minutes} minutes</span></div><ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">{(item.learning_objectives || []).map(objective => <li key={objective}>{objective}</li>)}</ul><div className="mt-4 space-y-2">{(item.activities || []).map((activity, index) => <div key={`${activity.title}-${index}`} className="rounded-lg border border-slate-200 bg-white p-3 text-sm"><div className="flex justify-between gap-3"><strong>{activity.title}</strong><span className="text-xs text-slate-500">{activity.duration_minutes}m</span></div><p className="mt-1 text-slate-500">{activity.description}</p></div>)}</div>{item.recommended_resources?.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{item.recommended_resources.map(resource => resource.url_or_ref ? <a key={resource.id} href={resource.url_or_ref} target="_blank" rel="noreferrer" className="inline-flex items-center rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-100">{resource.title}</a> : <span key={resource.id} className="rounded-lg bg-slate-200 px-3 py-1.5 text-xs text-slate-600">{resource.title}</span>)}</div>}</div></div></article>; })}</div> : <p className="mt-4 text-sm text-slate-500">Complete an assessment to generate your personalized study plan.</p>}</div>{resources.length > 0 && <div className="mt-6"><ResourceList resources={resources} /></div>}</AppShell>;
}
