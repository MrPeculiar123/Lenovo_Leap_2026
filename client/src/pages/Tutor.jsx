import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import AppShell from '../components/AppShell';
import Loading from '../components/Loading';
import ResourceList from '../components/ResourceList';
import { api } from '../services/api';

function normalizeMessageContent(value) {
  if (Array.isArray(value)) {
    return value.map(item => typeof item === 'object' ? item?.text || '' : String(item)).join('');
  }
  if (typeof value !== 'string') return value == null ? '' : String(value);
  if (!value.trim().startsWith('[{')) return value;
  const textParts = [...value.matchAll(/["']text["']\s*:\s*["']([\s\S]*)["']\s*,\s*["'](?:extras|signature)["']/g)];
  return textParts.length ? textParts.map(match => match[1].replace(/\\n/g, '\n')).join('') : value;
}

function normalizeMessages(history) {
  return (history || []).map(turn => ({
    ...turn,
    content: normalizeMessageContent(turn.content || turn.text || ''),
  }));
}

export default function Tutor() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [language, setLanguage] = useState('English');
  const [resources, setResources] = useState([]);
  const [feedback, setFeedback] = useState({});
  const [pendingFeedback, setPendingFeedback] = useState({});
  const loadingStarted = useRef(false);
  const sendingRef = useRef(false);

  useEffect(() => {
    if (loadingStarted.current) return undefined;
    loadingStarted.current = true;
    api.getDashboard()
      .then(data => {
        if (!data.assessment_id) throw new Error('Complete an assessment before starting a personalized tutor conversation.');
        setLanguage(data.language || 'English');
        setResources(data.grounded_resources || []);
        const savedHistory = data.tutor_chat_history || [];
        setMessages(normalizeMessages(savedHistory.length ? savedHistory : (data.tutor_explanation_localized ? [{ role: 'assistant', content: data.tutor_explanation_localized }] : [])));
        setLoading(false);
      })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  const send = async event => {
    event.preventDefault();
    if (!input.trim() || sending || sendingRef.current) return;
    const text = input.trim();
    setInput('');
    setSending(true);
    sendingRef.current = true;
    setError('');
    try {
      const result = await api.tutorChat(text, language);
      const nextMessages = normalizeMessages(result.chat_history);
      const lastMessageIndex = nextMessages.length - 1;
      if (result.message_id && nextMessages[lastMessageIndex]?.role === 'assistant') {
        nextMessages[lastMessageIndex] = { ...nextMessages[lastMessageIndex], message_id: result.message_id };
      }
      setMessages(nextMessages);
      setResources(result.grounded_resources || resources);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
      sendingRef.current = false;
    }
  };

  const submitFeedback = async (messageId, rating) => {
    if (feedback[messageId] || pendingFeedback[messageId]) return;
    setPendingFeedback(current => ({ ...current, [messageId]: true }));
    try {
      await api.submitTutorFeedback(messageId, rating);
      setFeedback(current => ({ ...current, [messageId]: 'Feedback recorded' }));
    } catch (err) {
      setError(err.message);
    } finally {
      setPendingFeedback(current => {
        const next = { ...current };
        delete next[messageId];
        return next;
      });
    }
  };

  if (loading) return <AppShell><Loading message="Loading your tutor context..." /></AppShell>;

  return (
    <AppShell>
      <div className="mx-auto max-w-4xl">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-indigo-600">Your study companion</p>
            <h1 className="mt-2 text-3xl font-bold">AI tutor</h1>
            <p className="mt-2 text-slate-500">Ask for an explanation, an example, or a nudge in the right direction.</p>
          </div>
          <label className="text-sm font-medium text-slate-600">
            Language
            <select value={language} onChange={event => setLanguage(event.target.value)} className="ml-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm">
              <option>English</option>
              <option>Hindi</option>
              <option>Marathi</option>
            </select>
          </label>
        </div>

        {error && <p className="mt-5 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}

        <div className="mt-8 flex min-h-120 flex-col rounded-2xl border border-slate-200 bg-white">
          <div className="flex-1 space-y-4 overflow-y-auto p-5">
            {messages.length === 0 && !error && (
              <div className="py-20 text-center text-sm text-slate-400">Try asking about your current learning plan.</div>
            )}
            {messages.map((message, index) => {
              const content = normalizeMessageContent(message.content || message.text || '');
              const isUser = message.role === 'user';
              return (
                <div key={`${message.role}-${index}`} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${isUser ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-800'}`}>
                    <div className={`tutor-markdown ${isUser ? 'tutor-markdown-user' : ''}`}>
                      <ReactMarkdown>{content}</ReactMarkdown>
                    </div>
                    {!isUser && message.message_id && (
                      feedback[message.message_id] ? (
                        <p className="mt-2 text-xs text-slate-500">{feedback[message.message_id]}</p>
                      ) : (
                        <div className="mt-3 flex gap-2 text-xs">
                          <button type="button" disabled={pendingFeedback[message.message_id]} onClick={() => submitFeedback(message.message_id, 1)} className="text-slate-500 hover:text-indigo-600 disabled:opacity-50">👍 Helpful</button>
                          <button type="button" disabled={pendingFeedback[message.message_id]} onClick={() => submitFeedback(message.message_id, -1)} className="text-slate-500 hover:text-rose-600 disabled:opacity-50">👎 Not helpful</button>
                        </div>
                      )
                    )}
                  </div>
                </div>
              );
            })}
            {sending && <p className="text-sm text-slate-400">Tutor is thinking...</p>}
          </div>

          <form onSubmit={send} className="flex gap-2 border-t border-slate-100 p-4">
            <input value={input} onChange={event => setInput(event.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-indigo-500" placeholder="Ask your tutor..." />
            <button disabled={sending || !input.trim()} className="rounded-xl bg-indigo-600 px-5 text-sm font-semibold text-white disabled:opacity-50">Send</button>
          </form>
        </div>

        <div className="mt-6">
          <ResourceList resources={resources} title="Resources used for this tutor context" />
        </div>
      </div>
    </AppShell>
  );
}