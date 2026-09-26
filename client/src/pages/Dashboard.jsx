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

const COPY = {
  English: { eyebrow: 'Your learning cockpit', title: 'Keep moving forward.', intro: 'A clear path to your next career milestone.', readiness: 'Career readiness', ready: 'You are career ready!', assess: 'Complete an assessment to get your score.', take: 'Take assessment', next: 'Next focus', recommendations: 'Your personalized recommendations appear here after an assessment.', plan: 'View learning plan', planCard: 'Learning plan', tutor: 'Ask your AI tutor', tutorText: 'Get clear explanations and guidance whenever you are stuck.', open: 'Open', domains: 'Domain progress', domainEmpty: 'Complete an assessment to see domain-level progress.', gaps: 'Priority gaps', noGaps: 'No priority gaps reported yet.', mastery: 'Concept mastery', noMastery: 'No concept scores yet.', preview: 'Study plan preview', noPlan: 'Your plan will appear after assessment analysis.' },
  Hindi: { eyebrow: 'आपका सीखने का केंद्र', title: 'आगे बढ़ते रहें।', intro: 'आपके अगले करियर लक्ष्य तक स्पष्ट मार्ग।', readiness: 'करियर तैयारी', ready: 'आप करियर के लिए तैयार हैं!', assess: 'स्कोर देखने के लिए आकलन पूरा करें।', take: 'आकलन लें', next: 'अगला फोकस', recommendations: 'आकलन के बाद आपकी व्यक्तिगत सिफारिशें यहाँ दिखाई देंगी।', plan: 'सीखने की योजना देखें', planCard: 'सीखने की योजना', tutor: 'AI ट्यूटर से पूछें', tutorText: 'जहाँ अटकें वहाँ स्पष्ट समझ और मार्गदर्शन पाएं।', open: 'खोलें', domains: 'डोमेन प्रगति', domainEmpty: 'डोमेन प्रगति देखने के लिए आकलन पूरा करें।', gaps: 'प्राथमिक कमियाँ', noGaps: 'अभी कोई प्राथमिक कमी नहीं मिली।', mastery: 'अवधारणा महारत', noMastery: 'अभी अवधारणा स्कोर नहीं हैं।', preview: 'योजना का पूर्वावलोकन', noPlan: 'आकलन विश्लेषण के बाद आपकी योजना दिखाई देगी।' },
  Marathi: { eyebrow: 'तुमचे शिक्षण केंद्र', title: 'पुढे चालत राहा.', intro: 'तुमच्या पुढील करिअर टप्प्यापर्यंतचा स्पष्ट मार्ग.', readiness: 'करिअर तयारी', ready: 'तुम्ही करिअरसाठी तयार आहात!', assess: 'स्कोअर पाहण्यासाठी मूल्यांकन पूर्ण करा.', take: 'मूल्यांकन घ्या', next: 'पुढील लक्ष', recommendations: 'मूल्यांकनानंतर तुमच्या वैयक्तिक शिफारसी येथे दिसतील.', plan: 'शिक्षण योजना पहा', planCard: 'शिक्षण योजना', tutor: 'AI ट्यूटरला विचारा', tutorText: 'अडचण आल्यावर स्पष्ट स्पष्टीकरण आणि मार्गदर्शन मिळवा.', open: 'उघडा', domains: 'डोमेन प्रगती', domainEmpty: 'डोमेन प्रगती पाहण्यासाठी मूल्यांकन पूर्ण करा.', gaps: 'प्राधान्याच्या उणिवा', noGaps: 'अजून प्राधान्याची उणीव नाही.', mastery: 'संकल्पना प्रभुत्व', noMastery: 'अजून संकल्पना स्कोअर नाहीत.', preview: 'शिक्षण योजनेचा आढावा', noPlan: 'मूल्यांकन विश्लेषणानंतर तुमची योजना दिसेल.' },
};

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
  const topGap = data?.priority_gaps?.[0];
  const topGapLabel = typeof topGap === "string"
    ? topGap
    : topGap?.career_skill || topGap?.root_cause_concept || "Discover your strengths";
  const copy = COPY[data?.language] || COPY.English;
  return (
    <AppShell>
      <div className="mb-8">
        <p className="mb-2 text-sm font-medium text-indigo-600">
          {copy.eyebrow}
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          {copy.title}
        </h1>
        <p className="mt-2 text-slate-500">
          {copy.intro}
        </p>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        <div className="rounded-2xl bg-indigo-600 p-6 text-white md:col-span-2">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-indigo-100">{copy.readiness}</p>
              <p className="mt-3 text-5xl font-bold">{score}%</p>
              <p className="mt-2 text-sm text-indigo-100">
                {data?.is_career_ready
                  ? copy.ready
                  : copy.assess}
              </p>
            </div>
            <Target className="opacity-60" size={28} />
          </div>
          <Link
            to="/assessment"
            className="mt-7 inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-semibold text-indigo-700"
          >
            {copy.take} <ArrowRight size={16} />
          </Link>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-6">
          <p className="text-sm text-slate-500">{copy.next}</p>
          <h2 className="mt-3 text-xl font-bold">
            {topGapLabel}
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            {copy.recommendations}
          </p>
          <Link
            to="/learning-plan"
            className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-indigo-600"
          >
            {copy.plan} <ArrowRight size={15} />
          </Link>
        </div>
      </div>
      <div className="mt-6 grid gap-5 md:grid-cols-2">
        <Card
          icon={BookOpen}
          title={copy.planCard}
          text={
            data?.plan_summary ||
            "Build a practical plan around your goals and available time."
          }
          href="/learning-plan"
          openLabel={copy.open}
        />
        <Card
          icon={Sparkles}
          title={copy.tutor}
          text={copy.tutorText}
          href="/tutor"
          openLabel={copy.open}
        />
      </div>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="flex items-center gap-2 font-bold">
            <BarChart3 size={19} className="text-indigo-600" /> {copy.domains}
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
              {copy.domainEmpty}
            </p>
          )}
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="flex items-center gap-2 font-bold">
            <CheckCircle2 size={19} className="text-indigo-600" /> {copy.gaps}
          </h2>
          {data?.priority_gaps?.length ? (
            <ul className="mt-4 space-y-3">
              {data.priority_gaps.slice(0, 5).map((gap, index) => (
                <li
                  key={`${gap}-${index}`}
                  className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700"
                >
                  {typeof gap === "string" ? (
                    gap
                  ) : (
                    <span>
                      <strong>{gap.career_skill || gap.name || gap.concept || "Skill gap"}</strong>
                      {gap.severity && <span className="ml-2 text-xs uppercase text-slate-500">{gap.severity}</span>}
                      {gap.root_cause_concept && <span className="mt-1 block text-xs text-slate-500">Root cause: {gap.root_cause_concept}</span>}
                      {gap.current_score != null && gap.required_benchmark != null && <span className="mt-1 block text-xs text-slate-500">Current {Math.round(gap.current_score * 100)}% | Required {Math.round(gap.required_benchmark * 100)}% | Gap {Math.round((gap.gap_size || 0) * 100)}%</span>}
                      {gap.prerequisite_path?.length > 0 && <span className="mt-1 block text-xs text-slate-500">Path: {gap.prerequisite_path.join(' -> ')}</span>}
                      <span className="mt-2 flex gap-3 text-xs font-semibold text-indigo-600"><Link to="/learning-plan">Open plan</Link><Link to="/tutor">Ask tutor</Link></span>
                    </span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              {copy.noGaps}
            </p>
          )}
        </section>
      </div>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="font-bold">{copy.mastery}</h2>
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
              {copy.noMastery}
            </p>
          )}
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="font-bold">{copy.preview}</h2>
          {data?.study_plan?.length ? (
            <ul className="mt-4 space-y-2 text-sm text-slate-600">
              {data.study_plan.slice(0, 3).map((item, i) => (
                <li key={i}>
                  •{" "}
                  {typeof item === "string"
                    ? item
                    : item.focus_topic || item.title || item.topic || item.description || "Planned activity"}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-slate-500">
              {copy.noPlan}
            </p>
          )}
        </section>
      </div>
    </AppShell>
  );
}

function Card({ icon: Icon, title, text, href, openLabel = "Open" }) {
  return (
    <Link
      to={href}
      className="group rounded-2xl border border-slate-200 bg-white p-6 transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-sm"
    >
      <Icon size={22} className="text-indigo-600" />
      <h2 className="mt-4 font-bold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-500">{text}</p>
      <span className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-indigo-600">
        {openLabel} <ArrowRight size={15} />
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