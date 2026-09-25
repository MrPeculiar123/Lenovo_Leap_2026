import { useEffect, useRef, useState } from 'react';
import AppShell from '../components/AppShell';
import { api } from '../services/api';
import { Empty } from './Dashboard';

const completedSession = session => session?.is_assessment_complete ?? session?.is_complete;

export default function Assessment() {
  const [session, setSession] = useState(null);
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [planning, setPlanning] = useState(false);
  const [planError, setPlanError] = useState('');
  const [restarting, setRestarting] = useState(false);
  const questionStartedAt = useRef(null);
  const pausedElapsed = useRef(0);

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

  useEffect(() => {
    if (!session?.question?.id || completedSession(session)) return undefined;
    questionStartedAt.current = performance.now();
    pausedElapsed.current = 0;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        if (questionStartedAt.current !== null) {
          pausedElapsed.current += performance.now() - questionStartedAt.current;
          questionStartedAt.current = null;
        }
      } else if (questionStartedAt.current === null) {
        questionStartedAt.current = performance.now();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [session?.question?.id]);

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

  const startNewAssessment = async () => {
    setRestarting(true);
    setError('');
    try {
      const next = await api.startAssessment({ restart: true });
      setSession(next);
      setAnswer('');
    } catch (err) {
      setError(err.message);
    } finally {
      setRestarting(false);
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
        response_time_sec: Math.max(1, Math.round((pausedElapsed.current + (questionStartedAt.current === null ? 0 : performance.now() - questionStartedAt.current)) / 1000)),
      });
      setSession(next);
      setAnswer('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const completed = completedSession(session);
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
            <Empty title="Assessment complete" text="Your readiness profile is ready. Review your results or start a new attempt when you are ready." />
            {session._debug && (
              <div className="mt-4 rounded-lg bg-slate-50 p-3 text-left text-xs text-slate-600">
                <div>Career: {session._debug.target_career} | Subject: {session._debug.subject}</div>
                <div>Language: {session._debug.language} | Question source: {session._debug.question_source || 'n/a'}</div>
                <div>Model: {session._debug.assessment_model}</div>
              </div>
            )}
            {planError && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{planError}</p>}
            <div className="mt-5 flex flex-wrap gap-3">
              {!hasPlan && (
                <button disabled={planning} onClick={generatePlan} className="rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">
                  {planning ? 'Generating plan...' : 'Retry plan generation'}
                </button>
              )}
              <button disabled={restarting} onClick={startNewAssessment} className="rounded-lg border border-indigo-200 px-5 py-3 text-sm font-semibold text-indigo-700 disabled:opacity-50">
                {restarting ? 'Starting...' : 'Start new assessment'}
              </button>
            </div>
          </div>
        ) : session ? (
          <form onSubmit={submit} className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
            <div className="mb-6 flex items-center justify-between text-sm text-slate-500">
              <span>Question {session.current_step || 1} of {session.total_steps || 8}</span>
              <span className="rounded-full bg-indigo-50 px-3 py-1 text-indigo-700">Adaptive</span>
            </div>
            <p className="mb-3 text-xs text-slate-400">Path: {session.target_career || 'Unknown'} | Subject: {session.subject || 'Unknown'} | Language: {session.language || 'Unknown'}</p>
            <h2 className="text-xl font-semibold leading-8">{question?.question || 'Loading question...'}</h2>
            {question?.source && <p className="mt-2 text-xs text-slate-400">Question source: {question.source}</p>}
            {session._debug && (
              <div className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
                Career: {session._debug.target_career} | Subject: {session._debug.subject} | Language: {session._debug.language} | Model: {session._debug.assessment_model}
              </div>
            )}
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
