'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, ChevronLeft, CheckCircle2, Sparkles, Heart, Brain, Zap, MessageSquare, Shield } from 'lucide-react';

interface Question {
  id: string;
  section: string;
  text: string;
  type: 'scale' | 'choice' | 'text';
  options?: string[];
}

const ONBOARDING_QUESTIONS: Question[] = [
  { id: 'extraversion_1', section: 'Personality', text: 'I am the life of the party.', type: 'scale' },
  { id: 'agreeableness_1', section: 'Personality', text: 'I am interested in people.', type: 'scale' },
  { id: 'conscientiousness_1', section: 'Personality', text: 'I am always prepared.', type: 'scale' },
  { id: 'neuroticism_1', section: 'Values', text: 'I get stressed out easily.', type: 'scale' },
  { id: 'openness_1', section: 'Values', text: 'I have a rich vocabulary.', type: 'scale' },
  { id: 'goal_1', section: 'Intentions', text: 'What are you looking for?', type: 'choice', options: ['Serious Relationship', 'Casual Dating', 'Friendship', 'Unsure'] },
  { id: 'bio_1', section: 'About You', text: 'Tell us something unique about yourself.', type: 'text' },
];

const SECTIONS = ['Personality', 'Values', 'Intentions', 'About You'];

export const OnboardingFlow: React.FC = () => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [isCompleted, setIsCompleted] = useState(false);

  const currentQuestion = ONBOARDING_QUESTIONS[currentIndex];
  const progress = ((currentIndex + 1) / ONBOARDING_QUESTIONS.length) * 100;

  const handleAnswer = (answer: any) => {
    setAnswers({ ...answers, [currentQuestion.id]: answer });
    if (currentIndex < ONBOARDING_QUESTIONS.length - 1) {
      setTimeout(() => setCurrentIndex(currentIndex + 1), 300);
    } else {
      setIsCompleted(true);
    }
  };

  const handleBack = () => {
    if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
  };

  if (isCompleted) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md mx-auto text-center space-y-8 p-8 bg-white rounded-3xl shadow-2xl border border-primary-50"
      >
        <div className="relative inline-block">
          <div className="absolute inset-0 bg-primary-200 rounded-full blur-2xl opacity-20 animate-pulse" />
          <CheckCircle2 size={80} className="text-primary-500 relative z-10 mx-auto" />
        </div>
        <div className="space-y-4">
          <h2 className="text-3xl font-black text-slate-800 tracking-tight">Profile Complete</h2>
          <p className="text-slate-500 leading-relaxed">
            Your psychological blueprint is ready. Our AI is now curating connections that resonate with your core values.
          </p>
        </div>
        <button className="w-full py-4 bg-primary-500 text-white rounded-2xl font-black text-lg shadow-xl hover:bg-primary-600 transition-all active:scale-95">
          View My Matches
        </button>
      </motion.div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      {/* Header & Progress */}
      <div className="mb-12 space-y-6">
        <div className="flex justify-between items-end">
          <div className="space-y-1">
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-primary-500">
              {currentQuestion.section}
            </span>
            <h2 className="text-2xl font-extrabold text-slate-800">
              Step {currentIndex + 1} of {ONBOARDING_QUESTIONS.length}
            </h2>
          </div>
          <div className="text-right">
            <span className="text-2xl font-black text-slate-300">{Math.round(progress)}%</span>
          </div>
        </div>
        <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            className="h-full bg-primary-500"
          />
        </div>
      </div>

      {/* Question Card */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentQuestion.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="bg-white p-10 rounded-[2.5rem] shadow-xl border border-slate-50 space-y-10"
        >
          <h3 className="text-3xl font-bold text-slate-800 leading-tight">
            {currentQuestion.text}
          </h3>

          <div className="space-y-4">
            {currentQuestion.type === 'scale' && (
              <div className="flex justify-between gap-2">
                {[1, 2, 3, 4, 5].map((val) => (
                  <button
                    key={val}
                    onClick={() => handleAnswer(val)}
                    className={`flex-1 h-16 rounded-2xl font-black text-xl transition-all border-2
                      ${answers[currentQuestion.id] === val
                        ? 'bg-primary-500 border-primary-500 text-white shadow-lg scale-105'
                        : 'bg-white border-slate-100 text-slate-400 hover:border-primary-200 hover:text-primary-500'}`}
                  >
                    {val}
                  </button>
                ))}
              </div>
            )}

            {currentQuestion.type === 'choice' && (
              <div className="grid grid-cols-1 gap-3">
                {currentQuestion.options?.map((opt) => (
                  <button
                    key={opt}
                    onClick={() => handleAnswer(opt)}
                    className="w-full p-5 text-left rounded-2xl font-bold border-2 border-slate-100 hover:border-primary-500 hover:bg-primary-50/50 transition-all text-slate-700"
                  >
                    {opt}
                  </button>
                ))}
              </div>
            )}

            {currentQuestion.type === 'text' && (
              <div className="space-y-4">
                <textarea
                  className="w-full p-5 h-40 rounded-2xl border-2 border-slate-100 focus:border-primary-500 focus:ring-0 transition-all outline-none resize-none text-slate-700 font-medium"
                  placeholder="Type your response here..."
                  onChange={(e) => setAnswers({ ...answers, [currentQuestion.id]: e.target.value })}
                  value={answers[currentQuestion.id] || ''}
                />
                <button
                  onClick={() => handleAnswer(answers[currentQuestion.id])}
                  disabled={!answers[currentQuestion.id]}
                  className="w-full py-4 bg-primary-500 text-white rounded-2xl font-black shadow-lg disabled:opacity-50"
                >
                  Continue
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Footer Nav */}
      <div className="mt-8 flex items-center justify-between">
        <button
          onClick={handleBack}
          disabled={currentIndex === 0}
          className="flex items-center gap-2 text-slate-400 font-bold disabled:opacity-0 transition-all hover:text-slate-600"
        >
          <ChevronLeft size={20} />
          Back
        </button>
        <div className="flex gap-2">
          {ONBOARDING_QUESTIONS.map((_, idx) => (
            <div
              key={idx}
              className={`h-1.5 rounded-full transition-all
                ${idx === currentIndex ? 'w-6 bg-primary-500' : 'w-1.5 bg-slate-200'}`}
            />
          ))}
        </div>
      </div>
    </div>
  );
};
