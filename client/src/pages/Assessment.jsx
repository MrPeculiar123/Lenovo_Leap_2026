import { useEffect, useState } from 'react';
import AppShell from '../components/AppShell';
import { api } from '../services/api';
import { Empty } from './Dashboard';

export default function Assessment() {
  const [session, setSession] = useState(null);
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState('');

  useEffect(() => {
    let active = true;
    const restoreAssessment = async () => {
      setLoading(true);
      setError('');
      try {
        const restored = await api.startAssessment();
        if (active) setSession(restored);
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    };

    restoreAssessment();
    return () => {
      active = false;
    };
  }, []);

  const generatePlan = async () => {
    setPlanning(true);
    setPlanError('');
    try {
      const result = await api.analyzeAndPlan({});
      setSession(current => ({ ...current, ...result, plan: result }));
    } catch (err) {
      setPlanError(err.message);
    } finally {
      setPlanning(false);
    }
  };

  const submit = async event => {
    event.preventDefault();
    if (!answer.trim()) return;
    setLoading(true);
    setError('');
    try {
      const next = await api.submitAnswer({
        assessment_id: session.session_id || session.assessment_id,
        question_id: session.question?.id,
        student_answer: answer,
        response_time_sec: 20,
      });
      setSession(next);
      setAnswer('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const completed = session?.is_assessment_complete ?? session?.is_complete;
  const question = session?.question || session?.current_question;
  const hasPlan = Boolean(session?.study_plan?.length || session?.plan?.study_plan?.length);

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <p className="text-sm font-medium text-indigo-600">Skill check</p>
        <h1 className="mt-2 text-3xl font-bold">Assessment</h1>
        <p className="mt-2 text-slate-500">Understand where you are today so we can shape the right path.</p>
        {error && <p className="mt-5 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

        {loading && !session ? (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500">Restoring your assessment...</div>
        ) : completed ? (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-8">
            <Empty title="Assessment complete" text="Your readiness profile is ready and your learning plan is being generated." />
            {planError && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{planError}</p>}
            {!hasPlan && (
              <button disabled={planning} onClick={generatePlan} className="mt-5 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">
                {planning ? 'Generating plan...' : 'Retry plan generation'}
              </button>
            )}
          </div>
        ) : session ? (
          <form onSubmit={submit} className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
            <div className="mb-6 flex items-center justify-between text-sm text-slate-500">
              <span>Question {session.current_step || 1} of {session.total_steps || 8}</span>
              <span className="rounded-full bg-indigo-50 px-3 py-1 text-indigo-700">Adaptive</span>
            </div>
            <h2 className="text-xl font-semibold leading-8">{question?.question || 'Loading question...'}</h2>
            {question?.options?.length > 0 && (
              <div className="mt-6 grid gap-3">
                {question.options.map(option => (
                  <button type="button" key={option} onClick={() => setAnswer(option)} className={`rounded-xl border p-4 text-left text-sm transition ${answer === option ? 'border-indigo-500 bg-indigo-50 text-indigo-700' : 'border-slate-200 hover:border-indigo-300'}`}>
                    {option}
                  </button>
                ))}
              </div>
            )}
            {(!question?.options?.length || (answer && !question.options.includes(answer))) && (
              <textarea value={answer} onChange={event => setAnswer(event.target.value)} className="mt-6 min-h-28 w-full rounded-xl border border-slate-200 p-4 text-sm outline-none focus:border-indigo-500" placeholder="Type your answer..." />
            )}
            {question?.options?.length > 0 && <input value={answer} onChange={event => setAnswer(event.target.value)} className="sr-only" aria-label="Selected answer" />}
            <button disabled={loading || !answer.trim()} className="mt-6 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">
              {loading ? 'Saving...' : 'Submit answer'}
            </button>
          </form>
        ) : null}
      </div>
    </AppShell>
  );
}
