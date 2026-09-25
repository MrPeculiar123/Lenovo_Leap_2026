import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Navbar from '../components/Navbar';
import Button from '../components/Button';
import Input from '../components/Input';
import {
  Target,
  Clock,
  Globe2,
  Brain,
  Check,
  ChevronRight,
  ChevronLeft,
  Sparkles,
  AlertCircle,
  BookOpen,
  Code2,
  CheckCircle2,
} from 'lucide-react';

const SUBJECT_OPTIONS = [
  'Data Analytics',
  'Data Science',
  'Business Intelligence',
  'Data Engineering',
  'Other',
];

const CAREER_GOALS = [
  'Data Analyst',
  'Business Intelligence Analyst',
  'Data Scientist',
  'Data Engineer',
];

const TIME_COMMITMENT_OPTIONS = [
  { label: '1–5 hours / week', value: 5 },
  { label: '6–10 hours / week', value: 10 },
  { label: '11–15 hours / week', value: 15 },
  { label: '16–20 hours / week', value: 20 },
  { label: '20+ hours / week', value: 25 },
];

const LANGUAGES = ['English', 'Hindi', 'Marathi'];

const SKILL_LEVELS = [
  {
    id: 'Beginner',
    title: 'Beginner',
    desc: 'New to the subject. Looking to build strong core fundamentals.',
  },
  {
    id: 'Intermediate',
    title: 'Intermediate',
    desc: 'Have foundational knowledge. Ready to tackle structured concepts & projects.',
  },
  {
    id: 'Advanced',
    title: 'Advanced',
    desc: 'Experienced practitioner. Aiming to master high-level topics & system design.',
  },
];

const PRIOR_EXPOSURE_OPTIONS = [
  'Programming',
  'Data Structures',
  'Algorithms',
  'Web Development',
  'Databases',
  'Machine Learning',
  'Cloud Computing',
  'Cybersecurity',
];

const QUESTION_TYPES = [
  { id: 'MCQ', label: 'Multiple Choice (MCQ)', desc: 'Quick diagnostic conceptual questions' },
  { id: 'Scenario-based', label: 'Scenario-based', desc: 'Real-world problem solving & case studies' },
  { id: 'Coding', label: 'Coding Challenges', desc: 'Hands-on algorithm & software development exercises' },
];

export function Onboarding() {
  const [step, setStep] = useState(1);
  const { completeOnboardingProfile } = useAuth();
  const navigate = useNavigate();

  // Form State
  const [subject, setSubject] = useState('Data Analytics');
  const [customSubject, setCustomSubject] = useState('');
  const [careerGoal, setCareerGoal] = useState('Data Analyst');
  const [customCareerGoal, setCustomCareerGoal] = useState('');
  const [timeCommitmentHrs, setTimeCommitmentHrs] = useState(15);

  const [primaryLanguage, setPrimaryLanguage] = useState('English');
  const [secondaryLanguage, setSecondaryLanguage] = useState('None');

  const [perceivedLevel, setPerceivedLevel] = useState('Intermediate');
  const [priorExposure, setPriorExposure] = useState(['Programming', 'Data Structures']);
  const [preferredQuestionTypes, setPreferredQuestionTypes] = useState(['MCQ', 'Coding']);

  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Toggle prior exposure pills
  const togglePriorExposure = (item) => {
    setPriorExposure((prev) =>
      prev.includes(item) ? prev.filter((i) => i !== item) : [...prev, item]
    );
  };

  // Toggle question types
  const toggleQuestionType = (typeId) => {
    setPreferredQuestionTypes((prev) =>
      prev.includes(typeId)
        ? prev.filter((t) => t !== typeId)
        : [...prev, typeId]
    );
  };

  const validateStep = (currentStep) => {
    setError('');
    if (currentStep === 1) {
      const finalSubject = subject === 'Other' ? customSubject.trim() : subject;
      const finalCareerGoal = careerGoal === 'Other' ? customCareerGoal.trim() : careerGoal;
      if (!finalSubject) {
        setError('Please select or specify a target subject.');
        return false;
      }
      if (!finalCareerGoal) {
        setError('Please select or specify your career goal.');
        return false;
      }
      if (!timeCommitmentHrs) {
        setError('Please select your weekly time commitment.');
        return false;
      }
    } else if (currentStep === 2) {
      if (!primaryLanguage) {
        setError('Please select a primary language.');
        return false;
      }
      if (secondaryLanguage !== 'None' && secondaryLanguage === primaryLanguage) {
        setError('Primary and secondary languages cannot be the same.');
        return false;
      }
    } else if (currentStep === 3) {
      if (!perceivedLevel) {
        setError('Please select your perceived skill level.');
        return false;
      }
      if (preferredQuestionTypes.length === 0) {
        setError('Please select at least one preferred question type.');
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      setStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    setError('');
    setStep((prev) => prev - 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateStep(3)) return;

    setIsSubmitting(true);
    setError('');

    const finalSubject = subject === 'Other' ? customSubject.trim() : subject;
    const finalCareerGoal = careerGoal === 'Other' ? customCareerGoal.trim() : careerGoal;
    const finalSecondaryLanguage = secondaryLanguage === 'None' ? null : secondaryLanguage;

    const payload = {
      subject: finalSubject,
      career_goal: finalCareerGoal,
      time_commitment_hrs: Number(timeCommitmentHrs),
      primary_language: primaryLanguage,
      secondary_language: finalSecondaryLanguage,
      perceived_level: perceivedLevel,
      prior_exposure: priorExposure,
      preferred_question_types: preferredQuestionTypes,
    };

    try {
      await completeOnboardingProfile(payload);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err.message || 'Failed to complete setup. Please check your answers.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />

      <div className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* Step Indicator Header */}
        <div className="mb-8 sm:mb-12">
          <div className="text-center mb-6">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-3 py-1 rounded-full border border-indigo-500/20">
              Personalized Setup
            </span>
            <h1 className="text-2xl sm:text-3xl font-bold text-white mt-2">Configure Your Navigator</h1>
            <p className="text-sm text-slate-400 mt-1">Help us customize your learning path and adaptive assessments</p>
          </div>

          {/* Stepper Bar */}
          <div className="flex items-center justify-between relative max-w-xl mx-auto">
            <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-slate-800 -translate-y-1/2 z-0" />
            <div
              className="absolute top-1/2 left-0 h-0.5 bg-indigo-500 -translate-y-1/2 z-0 transition-all duration-300"
              style={{ width: `${((step - 1) / 2) * 100}%` }}
            />

            {[
              { num: 1, title: 'Goals & Commitment' },
              { num: 2, title: 'Language Preferences' },
              { num: 3, title: 'Experience & Types' },
            ].map((s) => {
              const isActive = step === s.num;
              const isDone = step > s.num;

              return (
                <div key={s.num} className="relative z-10 flex flex-col items-center">
                  <div
                    className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300 ${
                      isDone
                        ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                        : isActive
                        ? 'bg-indigo-500 text-white ring-4 ring-indigo-500/20 shadow-lg shadow-indigo-500/30'
                        : 'bg-slate-900 border border-slate-800 text-slate-500'
                    }`}
                  >
                    {isDone ? <Check className="w-5 h-5" /> : s.num}
                  </div>
                  <span
                    className={`mt-2 text-xs font-medium hidden sm:block ${
                      isActive || isDone ? 'text-indigo-400' : 'text-slate-500'
                    }`}
                  >
                    {s.title}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Global Error message */}
        {error && (
          <div className="mb-6 max-w-2xl mx-auto p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center space-x-3">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form Container */}
        <div className="bg-slate-900/90 border border-slate-800/90 rounded-2xl p-6 sm:p-10 shadow-2xl backdrop-blur-xl">
          {/* STEP 1: GOALS & COMMITMENT */}
          {step === 1 && (
            <div className="space-y-8 animate-fadeIn">
              <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
                <Target className="w-6 h-6 text-indigo-400" />
                <div>
                  <h2 className="text-xl font-bold text-white">Target Domain & Career Goal</h2>
                  <p className="text-xs text-slate-400">Define what subject you want to master and your dream target role.</p>
                </div>
              </div>

              {/* Target Subject */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-300">Target Subject</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  {SUBJECT_OPTIONS.map((sub) => (
                    <button
                      key={sub}
                      type="button"
                      onClick={() => setSubject(sub)}
                      className={`p-3 rounded-xl border text-xs font-medium text-left transition-all ${
                        subject === sub
                          ? 'border-indigo-500 bg-indigo-500/10 text-white shadow-md'
                          : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                      }`}
                    >
                      {sub}
                    </button>
                  ))}
                </div>
                {subject === 'Other' && (
                  <div className="pt-2">
                    <Input
                      placeholder="Specify custom subject..."
                      value={customSubject}
                      onChange={(e) => setCustomSubject(e.target.value)}
                    />
                  </div>
                )}
              </div>

              {/* Career Goal */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-300">Career Goal</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  {CAREER_GOALS.map((goal) => (
                    <button
                      key={goal}
                      type="button"
                      onClick={() => setCareerGoal(goal)}
                      className={`p-3 rounded-xl border text-xs font-medium text-left transition-all ${
                        careerGoal === goal
                          ? 'border-indigo-500 bg-indigo-500/10 text-white shadow-md'
                          : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                      }`}
                    >
                      {goal}
                    </button>
                  ))}
                </div>
                {careerGoal === 'Other' && (
                  <div className="pt-2">
                    <Input
                      placeholder="Specify custom career goal..."
                      value={customCareerGoal}
                      onChange={(e) => setCustomCareerGoal(e.target.value)}
                    />
                  </div>
                )}
              </div>

              {/* Weekly Time Commitment */}
              <div className="space-y-3">
                <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-indigo-400" />
                  Weekly Time Commitment
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-5 gap-3">
                  {TIME_COMMITMENT_OPTIONS.map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      onClick={() => setTimeCommitmentHrs(item.value)}
                      className={`p-3.5 rounded-xl border text-center transition-all ${
                        timeCommitmentHrs === item.value
                          ? 'border-indigo-500 bg-indigo-500/10 text-indigo-300 font-semibold ring-1 ring-indigo-500/30'
                          : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <span className="block text-xs">{item.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: LANGUAGE PREFERENCES */}
          {step === 2 && (
            <div className="space-y-8 animate-fadeIn">
              <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
                <Globe2 className="w-6 h-6 text-indigo-400" />
                <div>
                  <h2 className="text-xl font-bold text-white">Language & Regional Preferences</h2>
                  <p className="text-xs text-slate-400">Choose your comfortable learning and assessment languages.</p>
                </div>
              </div>

              {/* Primary Language */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-300">Primary Learning Language *</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {LANGUAGES.map((lang) => (
                    <button
                      key={lang}
                      type="button"
                      onClick={() => setPrimaryLanguage(lang)}
                      className={`p-4 rounded-xl border text-center font-medium transition-all ${
                        primaryLanguage === lang
                          ? 'border-indigo-500 bg-indigo-500/10 text-white ring-1 ring-indigo-500/30'
                          : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      <div className="text-base font-semibold">{lang}</div>
                      <span className="text-[11px] text-slate-500 block mt-0.5">Primary UI & Questions</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Secondary Language */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-300">Secondary Language (Optional)</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {['None', ...LANGUAGES].map((lang) => {
                    const isDisabled = lang !== 'None' && lang === primaryLanguage;
                    return (
                      <button
                        key={lang}
                        type="button"
                        disabled={isDisabled}
                        onClick={() => setSecondaryLanguage(lang)}
                        className={`p-3 rounded-xl border text-center text-xs font-medium transition-all ${
                          isDisabled
                            ? 'opacity-30 border-slate-900 bg-slate-950 cursor-not-allowed text-slate-600'
                            : secondaryLanguage === lang
                            ? 'border-indigo-500 bg-indigo-500/10 text-white font-semibold'
                            : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        {lang === 'None' ? 'None (Single Language)' : lang}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: EXPERIENCE & QUESTION TYPES */}
          {step === 3 && (
            <div className="space-y-8 animate-fadeIn">
              <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
                <Brain className="w-6 h-6 text-indigo-400" />
                <div>
                  <h2 className="text-xl font-bold text-white">Skill Level & Preferred Assessment Formats</h2>
                  <p className="text-xs text-slate-400">Tell us your background so we can generate tailored diagnostic questions.</p>
                </div>
              </div>

              {/* Perceived Level Cards */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-300">Perceived Skill Level *</label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {SKILL_LEVELS.map((lvl) => (
                    <div
                      key={lvl.id}
                      onClick={() => setPerceivedLevel(lvl.id)}
                      className={`p-5 rounded-xl border cursor-pointer transition-all ${
                        perceivedLevel === lvl.id
                          ? 'border-indigo-500 bg-indigo-500/10 text-white ring-1 ring-indigo-500/40 shadow-lg'
                          : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold text-white text-base">{lvl.title}</span>
                        {perceivedLevel === lvl.id && (
                          <CheckCircle2 className="w-5 h-5 text-indigo-400" />
                        )}
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">{lvl.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Prior Exposure Pills */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-300">Prior Exposure & Topics</label>
                <div className="flex flex-wrap gap-2">
                  {PRIOR_EXPOSURE_OPTIONS.map((item) => {
                    const isSelected = priorExposure.includes(item);
                    return (
                      <button
                        key={item}
                        type="button"
                        onClick={() => togglePriorExposure(item)}
                        className={`px-3.5 py-2 rounded-xl text-xs font-medium border transition-all ${
                          isSelected
                            ? 'border-indigo-500 bg-indigo-500/20 text-indigo-200'
                            : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        {isSelected ? '✓ ' : '+ '} {item}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Preferred Question Types */}
              <div className="space-y-3">
                <label className="block text-sm font-medium text-slate-300">Preferred Question Formats *</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {QUESTION_TYPES.map((qt) => {
                    const isSelected = preferredQuestionTypes.includes(qt.id);
                    return (
                      <div
                        key={qt.id}
                        onClick={() => toggleQuestionType(qt.id)}
                        className={`p-4 rounded-xl border cursor-pointer transition-all ${
                          isSelected
                            ? 'border-indigo-500 bg-indigo-500/10 text-white ring-1 ring-indigo-500/30'
                            : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-semibold text-sm text-white">{qt.label}</span>
                          {isSelected && <Check className="w-4 h-4 text-indigo-400" />}
                        </div>
                        <p className="text-xs text-slate-400">{qt.desc}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Navigation Controls */}
          <div className="mt-10 pt-6 border-t border-slate-800/80 flex items-center justify-between">
            {step > 1 ? (
              <Button
                type="button"
                variant="outline"
                onClick={handleBack}
                disabled={isSubmitting}
                icon={ChevronLeft}
              >
                Back
              </Button>
            ) : (
              <div />
            )}

            {step < 3 ? (
              <Button
                type="button"
                variant="primary"
                onClick={handleNext}
              >
                Continue
                <ChevronRight className="w-4 h-4 ml-1.5" />
              </Button>
            ) : (
              <Button
                type="button"
                variant="primary"
                onClick={handleSubmit}
                isLoading={isSubmitting}
              >
                <Sparkles className="w-4 h-4 mr-2 text-indigo-300" />
                Complete Setup
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Onboarding;
