import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Button from '../components/Button';
import {
  Sparkles,
  Target,
  Clock,
  Globe,
  Brain,
  Layers,
  BookOpen,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Code,
  Edit3,
} from 'lucide-react';

export function Dashboard() {
  const { user, onboardingProfile } = useAuth();
  const [assessmentModalOpen, setAssessmentModalOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        {/* Welcome Header */}
        <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-900/60 border border-slate-800/80 p-6 rounded-2xl backdrop-blur-md">
          <div>
            <div className="flex items-center space-x-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-1">
              <Sparkles className="w-4 h-4" />
              <span>Learning Dashboard</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Welcome back 👋
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Let's build your learning journey.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              to="/onboarding"
              className="inline-flex items-center space-x-1.5 text-xs font-medium px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition"
            >
              <Edit3 className="w-3.5 h-3.5" />
              <span>Update Preferences</span>
            </Link>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Column: Assessment Session Card */}
          <div className="lg:col-span-2 space-y-8">
            {/* Assessment Session Card */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-950/90 via-slate-900 to-slate-950 border border-indigo-500/30 p-6 sm:p-8 shadow-2xl">
              {/* Background accent glow */}
              <div className="absolute -top-24 -right-24 w-64 h-64 bg-indigo-500/20 blur-3xl rounded-full pointer-events-none" />

              <div className="relative z-10">
                <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold mb-4">
                  <Brain className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Adaptive Engine Ready</span>
                </div>

                <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                  Assessment Session
                </h2>

                <p className="mt-2 text-slate-300 text-sm sm:text-base leading-relaxed">
                  Your personalized assessment is ready.
                </p>

                <div className="mt-6 space-y-3 bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    We'll use your profile to determine:
                  </p>
                  <ul className="space-y-2 text-sm text-slate-300">
                    <li className="flex items-center space-x-2.5">
                      <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
                      <span>Current knowledge baseline</span>
                    </li>
                    <li className="flex items-center space-x-2.5">
                      <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
                      <span>Strengths and core domain mastery</span>
                    </li>
                    <li className="flex items-center space-x-2.5">
                      <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
                      <span>Target skill gaps for {onboardingProfile?.career_goal || 'your goal'}</span>
                    </li>
                    <li className="flex items-center space-x-2.5">
                      <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
                      <span>Recommended learning path in {onboardingProfile?.primary_language || 'your language'}</span>
                    </li>
                  </ul>
                </div>

                <div className="mt-8">
                  <Button
                    variant="primary"
                    size="lg"
                    onClick={() => setAssessmentModalOpen(true)}
                  >
                    Start Assessment
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Assessment Modal Placeholder */}
            {assessmentModalOpen && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
                <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
                  <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-4">
                    <Brain className="w-6 h-6" />
                  </div>
                  <h3 className="text-xl font-bold text-white">Assessment Engine</h3>
                  <p className="text-slate-400 text-sm mt-2 leading-relaxed">
                    The adaptive assessment agent will generate custom {onboardingProfile?.preferred_question_types?.join(', ') || 'MCQ'} questions tailored for your {onboardingProfile?.perceived_level} level in {onboardingProfile?.primary_language}.
                  </p>
                  <div className="mt-4 p-3 bg-indigo-950/50 border border-indigo-800/40 rounded-xl text-xs text-indigo-300">
                    ✨ Phase 1 integration complete! Adaptive agent connection ready.
                  </div>
                  <div className="mt-6 flex justify-end">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => setAssessmentModalOpen(false)}
                    >
                      Got It
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar Column: Profile Summary */}
          <div className="space-y-6">
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-xl">
              <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Target className="w-5 h-5 text-indigo-400" />
                  Profile Summary
                </h3>
                <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  Active
                </span>
              </div>

              {onboardingProfile ? (
                <div className="space-y-4 text-sm">
                  {/* Subject */}
                  <div>
                    <span className="text-xs text-slate-400 block font-medium uppercase tracking-wider">Target</span>
                    <span className="text-base font-semibold text-white mt-0.5 block">
                      {onboardingProfile.subject}
                    </span>
                  </div>

                  {/* Career Goal */}
                  <div>
                    <span className="text-xs text-slate-400 block font-medium uppercase tracking-wider">Career Goal</span>
                    <span className="text-base font-semibold text-indigo-300 mt-0.5 block">
                      {onboardingProfile.career_goal}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-800/60">
                    {/* Skill Level */}
                    <div>
                      <span className="text-xs text-slate-400 block font-medium uppercase tracking-wider">Skill Level</span>
                      <span className="font-semibold text-slate-200 text-sm mt-0.5 block">
                        {onboardingProfile.perceived_level}
                      </span>
                    </div>

                    {/* Weekly Commitment */}
                    <div>
                      <span className="text-xs text-slate-400 block font-medium uppercase tracking-wider">Commitment</span>
                      <span className="font-semibold text-slate-200 text-sm mt-0.5 block">
                        {onboardingProfile.time_commitment_hrs} hours/wk
                      </span>
                    </div>
                  </div>

                  {/* Language */}
                  <div className="pt-2 border-t border-slate-800/60">
                    <span className="text-xs text-slate-400 block font-medium uppercase tracking-wider">Learning Language</span>
                    <span className="font-semibold text-slate-200 text-sm mt-0.5 block">
                      {onboardingProfile.primary_language}
                      {onboardingProfile.secondary_language && (
                        <span className="text-slate-400 text-xs font-normal"> ({onboardingProfile.secondary_language})</span>
                      )}
                    </span>
                  </div>

                  {/* Prior Exposure */}
                  {onboardingProfile.prior_exposure && onboardingProfile.prior_exposure.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/60">
                      <span className="text-xs text-slate-400 block font-medium uppercase tracking-wider mb-2">Prior Exposure</span>
                      <div className="flex flex-wrap gap-1.5">
                        {onboardingProfile.prior_exposure.map((item, idx) => (
                          <span
                            key={idx}
                            className="px-2 py-0.5 text-xs rounded-md bg-slate-800 border border-slate-700 text-slate-300"
                          >
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Question Types */}
                  {onboardingProfile.preferred_question_types && onboardingProfile.preferred_question_types.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/60">
                      <span className="text-xs text-slate-400 block font-medium uppercase tracking-wider mb-2">Assessment Formats</span>
                      <div className="flex flex-wrap gap-1.5">
                        {onboardingProfile.preferred_question_types.map((type, idx) => (
                          <span
                            key={idx}
                            className="px-2.5 py-1 text-xs rounded-md bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 font-medium"
                          >
                            {type}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-6 text-slate-400 text-xs">
                  <p>No profile details found.</p>
                  <Link to="/onboarding" className="mt-2 text-indigo-400 font-medium hover:underline inline-block">
                    Complete Onboarding
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default Dashboard;
