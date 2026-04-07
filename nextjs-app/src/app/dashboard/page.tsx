'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Heart, Sparkles, MessageCircle, Shield, User, MapPin, Zap } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const matches = [
    { id: '1', name: 'Sarah', compatibility: 82, stage: 'Values', lastActivity: '2 hours ago', status: 'ai_mediation' },
    { id: '2', name: 'Elena', compatibility: 75, stage: 'Icebreakers', lastActivity: '5 hours ago', status: 'ai_mediation' },
    { id: '3', name: 'Sophia', compatibility: 91, stage: 'Ready to Meet', lastActivity: '1 day ago', status: 'direct_chat' },
  ];

  return (
    <div className="min-h-screen bg-slate-50 p-8 space-y-12">
      {/* Header */}
      <div className="flex justify-between items-center max-w-5xl mx-auto">
        <div className="space-y-1">
          <h1 className="text-4xl font-black text-slate-800 tracking-tight">Your Journey</h1>
          <p className="text-slate-500 font-medium">3 active connections being guided by AI.</p>
        </div>
        <div className="flex items-center gap-4 bg-white p-2 rounded-2xl shadow-sm border border-slate-100">
          <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center text-white shadow-lg">
            <User size={24} />
          </div>
          <div className="pr-4">
            <p className="text-xs font-black uppercase tracking-widest text-slate-400">Account</p>
            <p className="text-sm font-bold text-slate-700">James Wilson</p>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Left: Active Matches */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-black text-slate-800 flex items-center gap-2">
            <Heart size={20} className="text-primary-500" />
            Active Guided Connections
          </h2>

          <div className="grid gap-4">
            {matches.map((match) => (
              <motion.div
                key={match.id}
                whileHover={{ y: -4 }}
                className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100 flex items-center justify-between group transition-all hover:shadow-xl"
              >
                <div className="flex items-center gap-6">
                  <div className="relative">
                    <div className="w-16 h-16 bg-gradient-to-br from-primary-100 to-primary-50 rounded-2xl flex items-center justify-center text-primary-500 font-black text-xl shadow-inner">
                      {match.name[0]}
                    </div>
                    <div className="absolute -bottom-1 -right-1 p-1 bg-white rounded-lg shadow-sm">
                      <Shield size={12} className="text-primary-500" />
                    </div>
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-xl font-bold text-slate-800">{match.name}</h3>
                    <div className="flex items-center gap-3 text-xs font-bold text-slate-400 uppercase tracking-widest">
                      <span className="flex items-center gap-1 text-primary-500 bg-primary-50 px-2 py-0.5 rounded-full">
                        <Bot size={12} />
                        {match.stage}
                      </span>
                      <span>•</span>
                      <span>Active {match.lastActivity}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-8">
                  <div className="text-right">
                    <div className="text-2xl font-black text-slate-800 leading-none">{match.compatibility}%</div>
                    <div className="text-[10px] font-black uppercase tracking-widest text-slate-400 mt-1">Match</div>
                  </div>
                  <Link href={`/conversation/${match.id}`}>
                    <button className="p-4 bg-slate-900 text-white rounded-2xl group-hover:bg-primary-500 transition-colors shadow-lg active:scale-95">
                      <MessageCircle size={24} />
                    </button>
                  </Link>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Right: Insights & Stats */}
        <div className="space-y-8">
          {/* AI Insights Card */}
          <div className="bg-gradient-to-br from-primary-600 to-primary-700 p-8 rounded-[2.5rem] text-white space-y-6 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-10">
              <Bot size={120} />
            </div>
            <div className="space-y-2 relative z-10">
              <div className="inline-flex items-center gap-2 bg-white/20 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">
                <Sparkles size={12} />
                AI Insight
              </div>
              <h3 className="text-2xl font-black leading-tight">Your communication style is diplomat-leaning.</h3>
              <p className="text-primary-100 text-sm leading-relaxed">
                You tend to bridge gaps in conversation naturally. Elena resonates well with this energy.
              </p>
            </div>
            <button className="w-full py-4 bg-white text-primary-600 rounded-2xl font-black shadow-lg hover:bg-primary-50 transition-colors relative z-10">
              View My Stats
            </button>
          </div>

          {/* Quick Actions */}
          <div className="bg-white p-8 rounded-[2.5rem] shadow-sm border border-slate-100 space-y-6">
            <h4 className="text-sm font-black uppercase tracking-widest text-slate-400">Readiness Actions</h4>
            <div className="grid gap-3">
              <button className="flex items-center gap-4 p-4 rounded-2xl border-2 border-slate-50 hover:border-primary-500 transition-all text-left">
                <div className="p-3 bg-primary-50 text-primary-500 rounded-xl">
                  <Zap size={20} />
                </div>
                <div>
                  <p className="font-bold text-slate-800">Quick Intro</p>
                  <p className="text-xs text-slate-400 font-medium">Invite a friend to connect</p>
                </div>
              </button>
              <button className="flex items-center gap-4 p-4 rounded-2xl border-2 border-slate-50 hover:border-primary-500 transition-all text-left">
                <div className="p-3 bg-accent-50 text-accent-500 rounded-xl">
                  <MapPin size={20} />
                </div>
                <div>
                  <p className="font-bold text-slate-800">Meeting Prep</p>
                  <p className="text-xs text-slate-400 font-medium">Tips for your first meet</p>
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
