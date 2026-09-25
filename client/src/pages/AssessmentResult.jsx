import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import AppShell from '../components/AppShell';
import Loading from '../components/Loading';
import { Empty } from './Dashboard';
import { api } from '../services/api';

export default function AssessmentResult() {
  const { assessmentId } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getAssessmentDetail(assessmentId).then(setData).catch(err => setError(err.message));
  }, [assessmentId]);

  if (!data && !error) return <AppShell><Loading message="Loading assessment result..." /></AppShell>;
  if (error) return <AppShell><Empty title="Unable to load result" text={error} /></AppShell>;

  return (
    <AppShell>
      <p className="text-sm font-medium text-indigo-600">Assessment result</p>
      <h1 className="mt-2 text-3xl font-bold">{data.target_career}</h1>
      <p className="mt-2 text-slate-500">{data.subject} | {data.language}</p>
      <div className="mt-8 grid gap-5 md:grid-cols-3">
        <Metric label="Readiness" value={`${Math.round(data.career_readiness_score || 0)}%`} />
        <Metric label="Questions" value={data.raw_responses?.length || 0} />
        <Metric label="Status" value={data.status_value} />
      </div>
      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="font-bold">Domain scores</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {Object.entries(data.domain_scores || {}).map(([domain, score]) => (
            <div key={domain} className="rounded-xl bg-slate-50 p-4 text-sm">
              <div className="flex justify-between"><span>{domain}</span><strong>{Math.round(score <= 1 ? score * 100 : score)}%</strong></div>
            </div>
          ))}
        </div>
      </section>
      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6">
        <h2 className="font-bold">Priority gaps</h2>
        <div className="mt-4 space-y-3">
          {(data.priority_gaps || []).map((gap, index) => (
            <div key={`${gap.career_skill}-${index}`} className="rounded-xl bg-slate-50 p-4 text-sm">
              <strong>{gap.career_skill}</strong>
              <p className="mt-1 text-slate-500">{gap.severity} gap: {Math.round((gap.current_score || 0) * 100)}% current vs {Math.round((gap.required_benchmark || 0) * 100)}% required</p>
            </div>
          ))}
        </div>
      </section>
    </AppShell>
  );
}

function Metric({ label, value }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-2xl font-bold capitalize">{value}</p></div>;
}
