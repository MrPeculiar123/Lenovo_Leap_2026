import { useEffect, useState } from 'react';
import AppShell from '../components/AppShell';
import Loading from '../components/Loading';
import { api } from '../services/api';

export default function Tutor() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getDashboard()
      .then(data => {
        if (!data.assessment_id) throw new Error('Complete an assessment before starting a personalized tutor conversation.');
        setLoading(false);
      })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  const send = async event => {
    event.preventDefault();
    if (!input.trim() || sending) return;
    const text = input.trim();
    setInput('');
    setSending(true);
    setError('');
    try {
      const result = await api.tutorChat(text);
      setMessages(result.chat_history?.map(turn => ({ role: turn.role, text: turn.content })) || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  if (loading) return <AppShell><Loading message="Loading your tutor context..." /></AppShell>;
  return <AppShell><div className="mx-auto max-w-3xl"><p className="text-sm font-medium text-indigo-600">Your study companion</p><h1 className="mt-2 text-3xl font-bold">AI tutor</h1><p className="mt-2 text-slate-500">Ask for an explanation, an example, or a nudge in the right direction.</p>{error && <p className="mt-5 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}<div className="mt-8 flex min-h-120 flex-col rounded-2xl border border-slate-200 bg-white"><div className="flex-1 space-y-4 overflow-y-auto p-5">{messages.length === 0 && !error && <div className="py-20 text-center text-sm text-slate-400">Try asking about your current learning plan.</div>}{messages.map((message, index) => <div key={`${message.role}-${index}`} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}><p className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700'}`}>{message.text}</p></div>)}{sending && <p className="text-sm text-slate-400">Tutor is thinking...</p>}</div><form onSubmit={send} className="flex gap-2 border-t border-slate-100 p-4"><input value={input} onChange={event => setInput(event.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-indigo-500" placeholder="Ask your tutor..." /><button disabled={sending || !input.trim()} className="rounded-xl bg-indigo-600 px-5 text-sm font-semibold text-white disabled:opacity-50">Send</button></form></div></div></AppShell>;
}
