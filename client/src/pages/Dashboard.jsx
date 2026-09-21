import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Target,
  BookOpen,
  Sparkles,
  AlertCircle,
  BarChart3,
  CheckCircle2,
} from "lucide-react";
import AppShell from "../components/AppShell";
import { api } from "../services/api";
import Loading from "../components/Loading";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const load = () => {
    setError("");
    api
      .getDashboard()
      .then(setData)
      .catch((e) => setError(e.message));
  };
  useEffect(load, []);
  if (!data && !error)
    return (
      <AppShell>
        <Loading message="Loading your workspace..." />
      </AppShell>
    );
  if (error)
    return (
      <AppShell>
        <Empty
          title="Could not load your dashboard"
          text={error}
          action={load}
        />
      </AppShell>
    );
  const score = Math.round(
    (data?.career_readiness_score || 0) *
      (data?.career_readiness_score <= 1 ? 100 : 1),
  );
  return (
    <AppShell>
      <div className="mb-8">
        <p className="mb-2 text-sm font-medium text-indigo-600">
          Your learning cockpit
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Keep moving forward.
        </h1>
        <p className="mt-2 text-slate-500">
          A clear path to your next career milestone.
        </p>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        <div className="rounded-2xl bg-indigo-600 p-6 text-white md:col-span-2">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-indigo-100">Career readiness</p>
              <p className="mt-3 text-5xl font-bold">{score}%</p>
              <p className="mt-2 text-sm text-indigo-100">
                {data?.is_career_ready
                  ? "You are career ready!"
                  : "Complete an assessment to get your score."}
              </p>
            </div>
            <Target className="opacity-60" size={28} />
          </div>
          <Link
            to="/assessment"
            className="mt-7 inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-indigo-700"
          >
            Take assessment <ArrowRight size={16} />
          </Link>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <p className="text-sm text-slate-500">Next focus</p>
          <h2 className="mt-3 text-xl font-bold">
            {data?.priority_gaps?.[0] || "Discover your strengths"}
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Your personalized recommendations appear here after an assessment.
          </p>
          <Link
            to="/learning-plan"
            className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-indigo-600"
          >
            View learning plan <ArrowRight size={15} />
          </Link>
        </div>
      </div>
      <div className="mt-6 grid gap-5 md:grid-cols-2">
        <Card
          icon={BookOpen}
          title="Learning plan"
          text={
            data?.plan_summary ||
            "Build a practical plan around your goals and available time."
          }
          href="/learning-plan"
        />
        <Card
          icon={Sparkles}
          title="Ask your AI tutor"
          text="Get clear explanations and guidance whenever you are stuck."
          href="/tutor"
        />
      </div>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="flex items-center gap-2 font-bold">
            <BarChart3 size={19} className="text-indigo-600" /> Domain progress
          </h2>
          {Object.keys(data?.domain_scores || {}).length ? (
            <div className="mt-5 space-y-4">
              {Object.entries(data.domain_scores).map(([name, value]) => (
                <div key={name}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span className="text-slate-600">{name}</span>
                    <span className="font-semibold">
                      {Math.round(value <= 1 ? value * 100 : value)}%
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-indigo-500"
                      style={{
                        width: `${Math.min(100, value <= 1 ? value * 100 : value)}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              Complete an assessment to see domain-level progress.
            </p>
          )}
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="flex items-center gap-2 font-bold">
            <CheckCircle2 size={19} className="text-indigo-600" /> Priority gaps
          </h2>
          {data?.priority_gaps?.length ? (
            <ul className="mt-4 space-y-3">
              {data.priority_gaps.slice(0, 5).map((gap, index) => (
                <li
                  key={`${gap}-${index}`}
                  className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700"
                >
                  {typeof gap === "string"
                    ? gap
                    : gap.name || gap.concept || JSON.stringify(gap)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              No priority gaps reported yet.
            </p>
          )}
        </section>
      </div>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="font-bold">Concept mastery</h2>
          {Object.keys(data?.concept_mastery || {}).length ? (
            <div className="mt-4 flex flex-wrap gap-2">
              {Object.entries(data.concept_mastery)
                .slice(0, 8)
                .map(([name, value]) => (
                  <span
                    key={name}
                    className="rounded-full bg-slate-100 px-3 py-2 text-xs text-slate-700"
                  >
                    {name}: {Math.round(value <= 1 ? value * 100 : value)}%
                  </span>
                ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              No concept scores yet.
            </p>
          )}
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="font-bold">Study plan preview</h2>
          {data?.study_plan?.length ? (
            <ul className="mt-4 space-y-2 text-sm text-slate-600">
              {data.study_plan.slice(0, 3).map((item, i) => (
                <li key={i}>
                  •{" "}
                  {typeof item === "string"
                    ? item
                    : item.title ||
                      item.topic ||
                      item.description ||
                      JSON.stringify(item)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              Your plan will appear after assessment analysis.
            </p>
          )}
        </section>
      </div>
    </AppShell>
  );
}
function Card({ icon: Icon, title, text, href }) {
  return (
    <Link
      to={href}
      className="group rounded-2xl border border-slate-200 bg-white p-6 transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-sm"
    >
      <Icon size={22} className="text-indigo-600" />
      <h2 className="mt-4 font-bold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-500">{text}</p>
      <span className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-indigo-600">
        Open <ArrowRight size={15} />
      </span>
    </Link>
  );
}
export function Empty({ title, text, action }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center">
      <AlertCircle className="mx-auto text-slate-300" size={30} />
      <h2 className="mt-4 font-bold">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">{text}</p>
      {action && (
        <button
          onClick={action}
          className="mt-5 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
        >
          Retry
        </button>
      )}
    </div>
  );
}
