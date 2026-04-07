'use client';

import { motion } from 'framer-motion';
import { Bot, ShieldCheck, Heart, Sparkles, Share2, MessageCircle } from 'lucide-react';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 text-center bg-gradient-to-br from-slate-50 to-primary-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="max-w-3xl space-y-8"
      >
        <div className="flex justify-center mb-6">
          <div className="relative p-6 bg-white rounded-full shadow-2xl ring-1 ring-primary-100">
            <Bot size={48} className="text-primary-500" />
            <motion.div
              animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
              transition={{ repeat: Infinity, duration: 2 }}
              className="absolute top-0 right-0 p-2 bg-accent-400 rounded-full text-white"
            >
              <Sparkles size={16} />
            </motion.div>
          </div>
        </div>

        <h1 className="text-5xl md:text-7xl font-black text-slate-800 tracking-tighter leading-tight">
          DateNow: <br />
          <span className="text-primary-500">AI-Guided</span> Readiness
        </h1>

        <p className="text-xl md:text-2xl text-slate-500 font-medium leading-relaxed max-w-2xl mx-auto">
          The premium, emotionally intelligent platform for relationship-minded people.
          Guided by AI. Grounded in trust. Built for connection.
        </p>

        <div className="flex flex-col md:flex-row gap-4 justify-center pt-8">
          <Link href="/onboarding">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-10 py-5 bg-primary-500 text-white rounded-2xl font-black text-lg shadow-xl hover:bg-primary-600 transition-colors flex items-center gap-3"
            >
              Start Your Journey
              <Sparkles size={20} />
            </motion.button>
          </Link>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="px-10 py-5 bg-white text-slate-800 border-2 border-slate-100 rounded-2xl font-black text-lg shadow-md hover:bg-slate-50 transition-colors"
          >
            Learn the Science
          </motion.button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-16">
          <FeatureCard
            icon={<ShieldCheck className="text-primary-500" />}
            title="Safe Discovery"
            desc="AI-moderated chat ensures every connection starts with respect and dignity."
          />
          <FeatureCard
            icon={<Heart className="text-accent-500" />}
            title="Deep Insights"
            desc="Explore values, lifestyle, and emotional pacing with an intelligent guide."
          />
          <FeatureCard
            icon={<Share2 className="text-slate-700" />}
            title="Shareable Growth"
            desc="Celebrate your connection milestones with beautifully visual reveal cards."
          />
        </div>
      </motion.div>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: React.ReactNode, title: string, desc: string }) {
  return (
    <div className="p-8 bg-white/50 backdrop-blur-md rounded-3xl border border-white/20 shadow-lg text-left space-y-4 hover:bg-white transition-all">
      <div className="p-3 bg-white rounded-2xl shadow-sm inline-block">{icon}</div>
      <h3 className="text-xl font-black text-slate-800 tracking-tight">{title}</h3>
      <p className="text-slate-500 text-sm leading-relaxed">{desc}</p>
    </div>
  );
}
