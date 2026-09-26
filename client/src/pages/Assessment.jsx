import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import AppShell from '../components/AppShell';
import { api } from '../services/api';
import { Empty } from './Dashboard';

const completedSession = session => session?.is_assessment_complete ?? session?.is_complete;

const adaptationMessages = {
  EASIER_QUESTION: 'Adapting difficulty...',
  SAME_DIFFICULTY: 'Keeping the difficulty at the right pace...',
  HARDER_QUESTION: 'Moving to a more challenging question...',
  PREREQUISITE_QUESTION: 'Exploring a prerequisite concept...',
};

const COPY = {
  English: { eyebrow: 'Skill check', title: 'Assessment', intro: 'Understand where you are today so we can shape the right path.', restoring: 'Restoring your assessment...', complete: 'Assessment complete', completeText: 'Your readiness profile is ready. Review your results or start a new attempt when you are ready.', retryPlan: 'Retry plan generation', newAttempt: 'Start new assessment', adaptive: 'Adaptive', submit: 'Submit answer', saving: 'Saving...', path: 'Path', subject: 'Subject', language: 'Language', question: 'Question' },
  Hindi: { eyebrow: 'कौशल जांच', title: 'आकलन', intro: 'आप आज कहाँ हैं यह समझकर हम आपके लिए सही सीखने का मार्ग बनाएंगे।', restoring: 'आपका आकलन फिर से लोड हो रहा है...', complete: 'आकलन पूरा हुआ', completeText: 'आपकी तैयारी की प्रोफ़ाइल तैयार है। परिणाम देखें या नया प्रयास शुरू करें।', retryPlan: 'योजना फिर बनाएं', newAttempt: 'नया आकलन शुरू करें', adaptive: 'अनुकूलित', submit: 'उत्तर जमा करें', saving: 'सहेजा जा रहा है...', path: 'मार्ग', subject: 'विषय', language: 'भाषा', question: 'प्रश्न' },
  Marathi: { eyebrow: 'कौशल्य तपासणी', title: 'मूल्यांकन', intro: 'तुमची सद्यस्थिती समजून योग्य शिकण्याचा मार्ग तयार करूया.', restoring: 'तुमचे मूल्यांकन पुन्हा लोड होत आहे...', complete: 'मूल्यांकन पूर्ण', completeText: 'तुमची तयारी प्रोफाइल तयार आहे. निकाल पहा किंवा नवीन प्रयत्न सुरू करा.', retryPlan: 'योजना पुन्हा तयार करा', newAttempt: 'नवीन मूल्यांकन सुरू करा', adaptive: 'अनुकूलित', submit: 'उत्तर पाठवा', saving: 'जतन होत आहे...', path: 'मार्ग', subject: 'विषय', language: 'भाषा', question: 'प्रश्न' },
};

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
  const copy = COPY[session?.language] || COPY.English;
  const adaptationMessage = adaptationMessages[session?.adaptation?.strategy];
  const formattedQuestion = (question?.question || '')
    .replace(/```(\w+)?\s*/g, '```$1\n')
    .replace(/(\}\]|\))\s+(?=[a-zA-Z_])/g, '$1\n');

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <p className="text-sm font-medium text-indigo-600">{copy.eyebrow}</p>
        <h1 className="mt-2 text-3xl font-bold">{copy.title}</h1>
        <p className="mt-2 text-slate-500">{copy.intro}</p>
        {error && <p className="mt-5 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

        {loading && !session ? (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500">{copy.restoring}</div>
        ) : completed ? (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-8">
            <Empty title={copy.complete} text={copy.completeText} />
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
                  {planning ? copy.saving : copy.retryPlan}
                </button>
              )}
              <button disabled={restarting} onClick={startNewAssessment} className="rounded-lg border border-indigo-200 px-5 py-3 text-sm font-semibold text-indigo-700 disabled:opacity-50">
                {restarting ? copy.saving : copy.newAttempt}
              </button>
            </div>
          </div>
        ) : session ? (
          <form onSubmit={submit} className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 sm:p-8">
            <div className="mb-6 flex items-center justify-between text-sm text-slate-500">
              <span>{copy.question} {session.current_step || 1} / {session.total_steps || 8}</span>
              <span className="rounded-full bg-indigo-50 px-3 py-1 text-indigo-700">{copy.adaptive}</span>
            </div>
            <p className="mb-3 text-xs text-slate-400">{copy.path}: {session.target_career || 'Unknown'} | {copy.subject}: {session.subject || 'Unknown'} | {copy.language}: {session.language || 'Unknown'}</p>
            {adaptationMessage && <p className="mb-3 text-xs text-indigo-600">{adaptationMessage}</p>}
            <div className="prose prose-slate max-w-none text-lg font-semibold text-slate-900">
              <ReactMarkdown>{formattedQuestion || 'Loading question...'}</ReactMarkdown>
            </div>
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
              {loading ? copy.saving : copy.submit}
            </button>
          </form>
        ) : null}
      </div>
    </AppShell>
  );
}
