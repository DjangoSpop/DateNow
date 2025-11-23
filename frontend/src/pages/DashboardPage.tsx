/**
 * Dashboard Page - Main user dashboard
 */
import { Link } from 'react-router-dom';
import { Heart, Users, MessageCircle, LogOut } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export default function DashboardPage() {
  const logout = useAuthStore((state) => state.logout);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Heart className="w-8 h-8 text-pink-600" fill="currentColor" />
            <span className="text-2xl font-bold text-gray-800">DateNow</span>
          </div>
          <button onClick={logout} className="flex items-center gap-2 text-gray-600 hover:text-gray-800">
            <LogOut className="w-5 h-5" />
            Logout
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-12">
        <h1 className="text-4xl font-bold text-gray-800 mb-8">Welcome to DateNow</h1>

        <div className="grid md:grid-cols-3 gap-6 max-w-5xl">
          <DashboardCard
            icon={<Users className="w-12 h-12 text-pink-600" />}
            title="Find Matches"
            description="Discover compatible people based on your psychological profile"
            link="/matches"
            linkText="View Matches"
          />
          <DashboardCard
            icon={<MessageCircle className="w-12 h-12 text-purple-600" />}
            title="AI Conversations"
            description="Engage in AI-mediated conversations with your matches"
            link="/matches"
            linkText="Active Chats"
          />
          <DashboardCard
            icon={<Heart className="w-12 h-12 text-pink-600" />}
            title="Your Profile"
            description="Update your profile and preferences"
            link="/dashboard"
            linkText="Edit Profile"
          />
        </div>

        <div className="mt-12 card max-w-2xl">
          <h2 className="text-2xl font-bold mb-4 text-gray-800">How AI Dating Works</h2>
          <div className="space-y-4 text-gray-600">
            <Step number={1} text="Browse compatible matches based on psychological profiling" />
            <Step number={2} text="Express interest in someone you like" />
            <Step number={3} text="If they're interested too, AI starts asking questions to both of you" />
            <Step number={4} text="Answer thoughtful questions that help you get to know each other" />
            <Step number={5} text="AI analyzes compatibility and facilitates introduction" />
            <Step number={6} text="Transition to direct messaging with confidence!" />
          </div>
        </div>
      </div>
    </div>
  );
}

function DashboardCard({ icon, title, description, link, linkText }: { icon: React.ReactNode; title: string; description: string; link: string; linkText: string }) {
  return (
    <div className="card hover:shadow-xl transition-shadow">
      <div className="mb-4">{icon}</div>
      <h3 className="text-xl font-bold mb-2 text-gray-800">{title}</h3>
      <p className="text-gray-600 mb-4">{description}</p>
      <Link to={link} className="text-pink-600 hover:text-pink-700 font-semibold">
        {linkText} →
      </Link>
    </div>
  );
}

function Step({ number, text }: { number: number; text: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex-shrink-0 w-8 h-8 bg-pink-600 text-white rounded-full flex items-center justify-center font-bold">
        {number}
      </div>
      <p className="pt-1">{text}</p>
    </div>
  );
}
