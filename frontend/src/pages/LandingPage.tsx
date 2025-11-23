/**
 * Landing Page
 */
import { Link } from 'react-router-dom';
import { Heart, Sparkles, MessageCircle, Shield } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-pink-600 via-purple-600 to-indigo-700 text-white">
        <div className="container mx-auto px-4 py-20">
          <div className="max-w-4xl mx-auto text-center">
            <div className="flex justify-center mb-6">
              <Heart className="w-16 h-16 text-pink-300" fill="currentColor" />
            </div>
            <h1 className="text-5xl md:text-6xl font-bold mb-6">
              Find Love Through <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-300 to-purple-300">
                AI-Guided Conversations
              </span>
            </h1>
            <p className="text-xl md:text-2xl mb-8 text-pink-100">
              DateNow uses AI to help you connect authentically before you even say hello.
              <br />
              No more awkward first messages. Just meaningful connections.
            </p>
            <div className="flex gap-4 justify-center">
              <Link to="/register" className="btn-primary text-lg px-8 py-3 bg-white text-pink-600 hover:bg-pink-50">
                Get Started Free
              </Link>
              <Link to="/login" className="btn-secondary text-lg px-8 py-3 bg-transparent border-2 border-white text-white hover:bg-white/10">
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-4xl font-bold text-center mb-12 text-gray-800">
            How It Works
          </h2>
          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <FeatureCard
              icon={<Sparkles className="w-12 h-12 text-pink-600" />}
              title="Psychological Profiling"
              description="Complete our science-based questionnaire to discover your personality, values, and relationship style."
            />
            <FeatureCard
              icon={<MessageCircle className="w-12 h-12 text-purple-600" />}
              title="AI-Mediated Introduction"
              description="Our AI asks both of you thoughtful questions separately, helping you get to know each other naturally."
            />
            <FeatureCard
              icon={<Heart className="w-12 h-12 text-pink-600" />}
              title="Meaningful Connections"
              description="Once the AI confirms compatibility, transition to direct messaging with confidence and context."
            />
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20 bg-gradient-to-br from-purple-50 to-pink-50">
        <div className="container mx-auto px-4">
          <h2 className="text-4xl font-bold text-center mb-12 text-gray-800">
            Why DateNow?
          </h2>
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <BenefitCard
              icon={<Shield className="w-10 h-10 text-pink-600" />}
              title="Quality Over Quantity"
              description="Only connect with people who truly match your values and personality."
            />
            <BenefitCard
              icon={<Sparkles className="w-10 h-10 text-purple-600" />}
              title="No Awkward Openers"
              description="Skip the small talk. Start conversations with context and confidence."
            />
            <BenefitCard
              icon={<MessageCircle className="w-10 h-10 text-pink-600" />}
              title="AI as Your Wingman"
              description="Let AI handle the introduction while you focus on being authentic."
            />
            <BenefitCard
              icon={<Heart className="w-10 h-10 text-purple-600" />}
              title="Science-Based Matching"
              description="Backed by psychological research on compatibility and relationships."
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-pink-600 to-purple-600 text-white">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold mb-6">Ready to Find Your Match?</h2>
          <p className="text-xl mb-8 text-pink-100">
            Join thousands of singles finding meaningful connections through AI-guided dating.
          </p>
          <Link to="/register" className="btn-primary text-lg px-8 py-3 bg-white text-pink-600 hover:bg-pink-50">
            Start Your Journey
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-8">
        <div className="container mx-auto px-4 text-center">
          <p>&copy; 2024 DateNow. All rights reserved.</p>
          <p className="mt-2">Built with AI to create meaningful human connections.</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="card text-center hover:shadow-xl transition-shadow">
      <div className="flex justify-center mb-4">{icon}</div>
      <h3 className="text-2xl font-bold mb-3 text-gray-800">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  );
}

function BenefitCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="flex gap-4 items-start">
      <div className="flex-shrink-0">{icon}</div>
      <div>
        <h3 className="text-xl font-bold mb-2 text-gray-800">{title}</h3>
        <p className="text-gray-600">{description}</p>
      </div>
    </div>
  );
}
