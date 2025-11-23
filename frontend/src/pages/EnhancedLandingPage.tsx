/**
 * Enhanced Landing Page with Calming Colors
 */
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Heart, Sparkles, MessageCircle, Shield, Brain, Target, CheckCircle } from 'lucide-react';

export default function EnhancedLandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-calm-50 via-white to-primary-50">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-500 via-primary-600 to-calm-500 opacity-10" />

        <div className="container mx-auto px-4 py-20 relative">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="max-w-5xl mx-auto text-center"
          >
            {/* Floating Hearts Animation */}
            <div className="relative mb-8">
              <motion.div
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 3, repeat: Infinity }}
                className="inline-block"
              >
                <Heart className="w-20 h-20 text-primary-500 mx-auto" fill="currentColor" />
              </motion.div>
              <motion.div
                animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="absolute inset-0 -z-10"
              >
                <div className="w-20 h-20 mx-auto bg-primary-200 rounded-full blur-xl" />
              </motion.div>
            </div>

            <h1 className="text-6xl md:text-7xl font-bold text-gray-800 mb-6">
              Find Love Through
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-500 to-accent-500">
                AI-Guided Conversations
              </span>
            </h1>

            <p className="text-xl md:text-2xl text-gray-600 mb-10 max-w-3xl mx-auto leading-relaxed">
              DateNow uses advanced AI to facilitate meaningful connections. Get to know each other
              through thoughtful conversations before the first hello.
            </p>

            <div className="flex flex-wrap gap-4 justify-center mb-8">
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Link
                  to="/register"
                  className="bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white font-bold py-4 px-10 rounded-full text-lg shadow-lg transition-all"
                >
                  Get Started Free
                </Link>
              </motion.div>
              <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                <Link
                  to="/login"
                  className="bg-white hover:bg-gray-50 text-primary-600 font-bold py-4 px-10 rounded-full text-lg shadow-md border-2 border-primary-200 transition-all"
                >
                  Sign In
                </Link>
              </motion.div>
            </div>

            <div className="flex items-center justify-center gap-8 text-sm text-gray-600">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-trust-500" />
                <span>100% Free to Start</span>
              </div>
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-trust-500" />
                <span>Verified Profiles</span>
              </div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-trust-500" />
                <span>AI-Powered Matching</span>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-5xl font-bold text-gray-800 mb-4">
              How DateNow Works
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Our AI moderator helps you connect authentically with compatible matches
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <StepCard
              number={1}
              icon={<Brain className="w-12 h-12" />}
              title="Complete Your Profile"
              description="Take our science-based psychological assessment to understand your personality, values, and relationship style"
              delay={0.2}
            />
            <StepCard
              number={2}
              icon={<MessageCircle className="w-12 h-12" />}
              title="AI Asks Questions"
              description="Our AI moderator conducts separate conversations with both of you, asking thoughtful questions to assess compatibility"
              delay={0.4}
            />
            <StepCard
              number={3}
              icon={<Heart className="w-12 h-12" />}
              title="Connect Authentically"
              description="Once compatibility is confirmed, transition to direct messaging with confidence and context"
              delay={0.6}
            />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-gradient-to-br from-calm-50 to-primary-50">
        <div className="container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-5xl font-bold text-gray-800 mb-4">
              Why Choose DateNow?
            </h2>
            <p className="text-xl text-gray-600">
              Dating reimagined with AI-powered authenticity
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
            <FeatureCard
              icon={<Shield className="w-10 h-10 text-primary-500" />}
              title="Verified & Safe"
              description="Multi-step verification prevents bots and scams"
              delay={0.1}
            />
            <FeatureCard
              icon={<Brain className="w-10 h-10 text-primary-500" />}
              title="Science-Based"
              description="Matching based on psychological compatibility"
              delay={0.2}
            />
            <FeatureCard
              icon={<Sparkles className="w-10 h-10 text-accent-500" />}
              title="Quality Over Quantity"
              description="Focus on meaningful connections, not endless swiping"
              delay={0.3}
            />
            <FeatureCard
              icon={<Target className="w-10 h-10 text-accent-500" />}
              title="AI Guidance"
              description="Get relationship insights throughout your journey"
              delay={0.4}
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-primary-600 to-primary-700 text-white">
        <div className="container mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-5xl font-bold mb-6">Ready to Find Your Match?</h2>
            <p className="text-xl mb-10 text-primary-100 max-w-2xl mx-auto">
              Join thousands of singles finding meaningful connections through AI-guided dating
            </p>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Link
                to="/register"
                className="inline-block bg-white text-primary-600 font-bold py-4 px-12 rounded-full text-lg shadow-xl hover:shadow-2xl transition-all"
              >
                Start Your Journey
              </Link>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Heart className="w-6 h-6 text-primary-400" fill="currentColor" />
                <span className="text-xl font-bold text-white">DateNow</span>
              </div>
              <p className="text-sm">
                AI-moderated dating for meaningful connections
              </p>
            </div>
            <div>
              <h3 className="text-white font-semibold mb-4">Product</h3>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">How it works</a></li>
                <li><a href="#" className="hover:text-white">Features</a></li>
                <li><a href="#" className="hover:text-white">Pricing</a></li>
              </ul>
            </div>
            <div>
              <h3 className="text-white font-semibold mb-4">Company</h3>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">About us</a></li>
                <li><a href="#" className="hover:text-white">Blog</a></li>
                <li><a href="#" className="hover:text-white">Careers</a></li>
              </ul>
            </div>
            <div>
              <h3 className="text-white font-semibold mb-4">Legal</h3>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">Privacy</a></li>
                <li><a href="#" className="hover:text-white">Terms</a></li>
                <li><a href="#" className="hover:text-white">Safety</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 text-center text-sm">
            <p>&copy; 2024 DateNow. All rights reserved.</p>
            <p className="mt-2">Built with AI to create meaningful human connections 💙</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function StepCard({ number, icon, title, description, delay }: any) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.5 }}
      className="relative"
    >
      <div className="absolute -top-4 -left-4 w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-600 rounded-full flex items-center justify-center text-white font-bold text-xl shadow-lg">
        {number}
      </div>
      <div className="card hover:shadow-2xl transition-all duration-300 pt-8">
        <div className="text-primary-500 mb-4">{icon}</div>
        <h3 className="text-2xl font-bold text-gray-800 mb-3">{title}</h3>
        <p className="text-gray-600 leading-relaxed">{description}</p>
      </div>
    </motion.div>
  );
}

function FeatureCard({ icon, title, description, delay }: any) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.3 }}
      whileHover={{ scale: 1.05, y: -5 }}
      className="card text-center hover:shadow-2xl transition-all duration-300"
    >
      <div className="flex justify-center mb-4">{icon}</div>
      <h3 className="text-xl font-bold text-gray-800 mb-2">{title}</h3>
      <p className="text-gray-600 text-sm">{description}</p>
    </motion.div>
  );
}
