import { Link } from 'react-router-dom';
import { Compass, Target, BrainCircuit, Globe2, Sparkles, ArrowRight, CheckCircle2, ShieldCheck, Zap } from 'lucide-react';
import Navbar from '../components/Navbar';

export function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      <Navbar />

      {/* Hero Section */}
      <section className="relative pt-16 pb-24 md:pt-24 md:pb-32 overflow-hidden">
        {/* Background glow effects */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-gradient-to-tr from-indigo-600/20 to-violet-600/20 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute top-10 right-10 w-72 h-72 bg-indigo-500/10 blur-[90px] rounded-full pointer-events-none" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
          {/* Badge */}
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-slate-900/90 border border-slate-800 text-xs text-indigo-400 font-medium mb-8 backdrop-blur-sm shadow-inner">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Next-Generation Career Navigation</span>
          </div>

          {/* Heading */}
          <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-[1.15]">
            AI-Powered Career & Skill Navigation in{' '}
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              Regional Languages
            </span>
          </h1>

          {/* Supporting Text */}
          <p className="mt-6 text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Navigate your career with confidence. Assess your current skill level, pinpoint learning gaps, and receive personalized learning paths tailored to your schedule and preferred language.
          </p>

          {/* CTAs */}
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/login"
              className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow-lg shadow-indigo-600/30 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] group text-base"
            >
              <span>Get Started Free</span>
              <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              to="/login"
              className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 hover:text-white font-semibold border border-slate-800 transition-all duration-200 text-base"
            >
              Sign In
            </Link>
          </div>

          {/* Key Value Pill Highlights */}
          <div className="mt-16 pt-8 border-t border-slate-900 grid grid-cols-2 md:grid-cols-4 gap-4 text-left max-w-4xl mx-auto">
            <div className="flex items-center space-x-3 text-slate-400 text-sm">
              <CheckCircle2 className="w-5 h-5 text-indigo-400 shrink-0" />
              <span>Adaptive Questioning</span>
            </div>
            <div className="flex items-center space-x-3 text-slate-400 text-sm">
              <CheckCircle2 className="w-5 h-5 text-indigo-400 shrink-0" />
              <span>Real-time Skill Gap Analysis</span>
            </div>
            <div className="flex items-center space-x-3 text-slate-400 text-sm">
              <CheckCircle2 className="w-5 h-5 text-indigo-400 shrink-0" />
              <span>Multi-Language Learning</span>
            </div>
            <div className="flex items-center space-x-3 text-slate-400 text-sm">
              <CheckCircle2 className="w-5 h-5 text-indigo-400 shrink-0" />
              <span>Personalized Goals</span>
            </div>
          </div>
        </div>
      </section>

      {/* Main Features Section */}
      <section className="py-20 bg-slate-900/50 border-y border-slate-800/60 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
              Engineered for Accelerating Your Growth
            </h2>
            <p className="mt-4 text-slate-400">
              Everything you need to benchmark your skills, discover growth opportunities, and execute your career roadmap.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Feature 1 */}
            <div className="p-8 rounded-2xl bg-slate-950/80 border border-slate-800/80 hover:border-indigo-500/40 transition-all duration-300 group hover:shadow-xl hover:shadow-indigo-500/5">
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <BrainCircuit className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Adaptive Assessments</h3>
              <p className="text-slate-400 leading-relaxed text-sm sm:text-base">
                Assess your current knowledge with intelligent, dynamic questions (MCQ, scenario-based, and coding) that adapt to your performance to pinpoint your exact baseline.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-8 rounded-2xl bg-slate-950/80 border border-slate-800/80 hover:border-violet-500/40 transition-all duration-300 group hover:shadow-xl hover:shadow-violet-500/5">
              <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/20 text-violet-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Target className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Skill Gap Analysis</h3>
              <p className="text-slate-400 leading-relaxed text-sm sm:text-base">
                Clear visualization of the precise gap between your current skill level and your target career goal—whether Software Engineer, Data Scientist, or AI Engineer.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-8 rounded-2xl bg-slate-950/80 border border-slate-800/80 hover:border-indigo-500/40 transition-all duration-300 group hover:shadow-xl hover:shadow-indigo-500/5">
              <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Zap className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Personalized Learning</h3>
              <p className="text-slate-400 leading-relaxed text-sm sm:text-base">
                Receive customized learning pathways tailored specifically to your weekly time commitment, target subject, and prior domain exposure.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-8 rounded-2xl bg-slate-950/80 border border-slate-800/80 hover:border-pink-500/40 transition-all duration-300 group hover:shadow-xl hover:shadow-pink-500/5">
              <div className="w-12 h-12 rounded-xl bg-pink-500/10 border border-pink-500/20 text-pink-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <Globe2 className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Multilingual Learning</h3>
              <p className="text-slate-400 leading-relaxed text-sm sm:text-base">
                Break language barriers by selecting your preferred primary and secondary languages, including English, Hindi, and Marathi.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Footer Section */}
      <section className="py-16 relative">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white">Ready to Navigate Your Learning Journey?</h2>
          <p className="mt-4 text-slate-400">Join thousands of learners building their future today.</p>
          <div className="mt-8">
            <Link
              to="/login"
              className="inline-flex items-center px-8 py-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow-lg shadow-indigo-600/30 transition-all duration-200"
            >
              Start Free Onboarding
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto py-8 border-t border-slate-900 bg-slate-950 text-center text-xs text-slate-500">
        <p>© 2026 Learning Navigator. Built for Lenovo Leap 2026. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default Landing;
