/**
 * Matches Page - View and manage matches
 */
import { Link } from 'react-router-dom';
import { Heart, MessageCircle, ArrowLeft } from 'lucide-react';

export default function MatchesPage() {
  // Mock data for demonstration
  const matches = [
    {
      id: 1,
      name: 'Sarah',
      age: 28,
      bio: 'Coffee enthusiast, loves hiking and photography',
      compatibility: 0.87,
      status: 'pending',
    },
    {
      id: 2,
      name: 'Emily',
      age: 26,
      bio: 'Artist and yoga teacher, passionate about sustainable living',
      compatibility: 0.82,
      status: 'ai_mediation',
    },
  ];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/dashboard" className="text-gray-600 hover:text-gray-800">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <div className="flex items-center gap-2">
            <Heart className="w-8 h-8 text-pink-600" fill="currentColor" />
            <span className="text-2xl font-bold text-gray-800">Your Matches</span>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 mb-8">Compatible Matches</h1>

          <div className="space-y-6">
            {matches.map((match) => (
              <MatchCard key={match.id} match={match} />
            ))}
          </div>

          {matches.length === 0 && (
            <div className="card text-center py-12">
              <Heart className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-600 mb-2">No matches yet</h3>
              <p className="text-gray-500">
                Check back soon! We're finding compatible people for you.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MatchCard({ match }: { match: any }) {
  return (
    <div className="card hover:shadow-xl transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-2xl font-bold text-gray-800">
            {match.name}, {match.age}
          </h3>
          <p className="text-gray-600 mt-1">{match.bio}</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-pink-600">
            {Math.round(match.compatibility * 100)}%
          </div>
          <div className="text-sm text-gray-500">Compatibility</div>
        </div>
      </div>

      <div className="flex gap-3 mt-6">
        {match.status === 'pending' && (
          <>
            <button className="btn-primary flex-1">
              <Heart className="w-5 h-5 inline mr-2" />
              Express Interest
            </button>
            <button className="btn-secondary">Pass</button>
          </>
        )}
        {match.status === 'ai_mediation' && (
          <Link to={`/ai-conversation/${match.id}`} className="btn-primary flex-1 text-center">
            <MessageCircle className="w-5 h-5 inline mr-2" />
            Continue AI Conversation
          </Link>
        )}
      </div>
    </div>
  );
}
