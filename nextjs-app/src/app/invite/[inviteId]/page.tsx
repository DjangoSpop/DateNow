'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Heart, ShieldCheck, Sparkles, ChevronRight, User } from 'lucide-react';
import Link from 'next/link';

export default function InvitationPage({ params }: { params: { inviteId: string } }) {
  // Mock data for invitation
  const invitation = {
    inviterName: 'James Wilson',
    inviterPhoto: null,
    type: 'Guided Connection',
    customMessage: "I'd love to try this AI-guided connection with you. It feels safer and more thoughtful than just chatting.",
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-calm-50 via-white to-primary-50 flex items-center justify-center p-8">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-xl w-full bg-white rounded-[3rem] shadow-2xl border border-primary-50 overflow-hidden relative"
      >
        <div className="absolute top-0 right-0 p-8 opacity-5">
          <Bot size={160} />
        </div>

        <div className="p-12 space-y-10 text-center relative z-10">
          {/* Inviter Info */}
          <div className="space-y-4">
            <div className="flex justify-center -space-x-4">
              <div className="w-20 h-20 bg-primary-100 rounded-3xl border-4 border-white flex items-center justify-center text-primary-600 font-black text-2xl shadow-lg relative z-10">
                {invitation.inviterName[0]}
              </div>
              <div className="w-20 h-20 bg-accent-100 rounded-3xl border-4 border-white flex items-center justify-center text-accent-600 shadow-lg translate-y-2">
                <Bot size={40} />
              </div>
            </div>
            <div className="space-y-1">
              <h1 className="text-3xl font-black text-slate-800 tracking-tight">
                {invitation.inviterName} invited you
              </h1>
              <p className="text-sm font-bold uppercase tracking-widest text-primary-500 bg-primary-50 py-1 px-4 rounded-full inline-block">
                to a {invitation.type}
              </p>
            </div>
          </div>

          {/* Custom Message */}
          <div className="bg-slate-50 p-8 rounded-3xl border border-slate-100 italic text-slate-600 leading-relaxed relative shadow-inner">
            <div className="absolute -top-3 left-8 bg-white px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest text-slate-400 border border-slate-100">
              Message from {invitation.inviterName}
            </div>
            "{invitation.customMessage}"
          </div>

          {/* Benefits */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
            <BenefitCard
              icon={<ShieldCheck size={18} />}
              title="Safe Space"
              desc="AI-moderated chat ensures respect."
            />
            <BenefitCard
              icon={<Sparkles size={18} />}
              title="Deep Insights"
              desc="Reveal core values naturally."
            />
          </div>

          {/* Actions */}
          <div className="space-y-4">
            <Link href="/onboarding">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full py-5 bg-primary-500 text-white rounded-2xl font-black text-xl shadow-xl hover:bg-primary-600 transition-all flex items-center justify-center gap-3"
              >
                Accept Invitation
                <ChevronRight size={24} />
              </motion.button>
            </Link>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-300">
              Free • AI-Powered • Secure
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

function BenefitCard({ icon, title, desc }: { icon: React.ReactNode, title: string, desc: string }) {
  return (
    <div className="p-4 bg-white border border-slate-100 rounded-2xl flex gap-3 shadow-sm">
      <div className="text-primary-500">{icon}</div>
      <div className="space-y-0.5">
        <h4 className="text-xs font-black text-slate-800 tracking-tight leading-none">{title}</h4>
        <p className="text-[10px] text-slate-400 font-medium leading-tight">{desc}</p>
      </div>
    </div>
  );
}
