/**
 * AI Conversation Page - AI-mediated conversation interface
 */
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Bot, Send, ArrowLeft, Sparkles } from 'lucide-react';

export default function AIConversationPage() {
  const { matchId } = useParams();
  const [currentQuestion, setCurrentQuestion] = useState(
    "Let's start with something light - what's a perfect weekend look like for you?"
  );
  const [answer, setAnswer] = useState('');
  const [questionNumber, setQuestionNumber] = useState(1);
  const [totalQuestions] = useState(10);
  const [conversationHistory, setConversationHistory] = useState<
    Array<{ question: string; answer: string; insight?: string }>
  >([]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!answer.trim()) return;

    // Add to history
    setConversationHistory([
      ...conversationHistory,
      {
        question: currentQuestion,
        answer: answer,
        insight: 'Your response shows a balanced approach to work-life harmony and value for meaningful relationships.',
      },
    ]);

    // Simulate next question
    setQuestionNumber(questionNumber + 1);
    if (questionNumber < totalQuestions) {
      setCurrentQuestion('What role does communication play in your ideal relationship?');
    }

    setAnswer('');
  };

  const progress = (questionNumber / totalQuestions) * 100;

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-white">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link to="/matches" className="text-gray-600 hover:text-gray-800">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <Bot className="w-8 h-8 text-purple-600" />
          <div>
            <h1 className="text-xl font-bold text-gray-800">AI-Mediated Conversation</h1>
            <p className="text-sm text-gray-500">
              Question {questionNumber} of {totalQuestions}
            </p>
          </div>
        </div>
      </header>

      {/* Progress Bar */}
      <div className="bg-white border-b">
        <div className="container mx-auto px-4">
          <div className="h-2 bg-gray-200">
            <div
              className="h-full bg-gradient-to-r from-pink-500 to-purple-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Info Card */}
          <div className="card bg-gradient-to-r from-purple-100 to-pink-100 border-2 border-purple-200">
            <div className="flex gap-3">
              <Sparkles className="w-6 h-6 text-purple-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-800 mb-1">How this works</h3>
                <p className="text-sm text-gray-700">
                  I'm asking both of you questions to help you get to know each other. Be authentic -
                  your responses help assess compatibility. Your match is answering similar questions
                  separately.
                </p>
              </div>
            </div>
          </div>

          {/* Conversation History */}
          {conversationHistory.map((item, index) => (
            <div key={index} className="space-y-3">
              <div className="card bg-purple-50 border-2 border-purple-200">
                <div className="flex gap-3">
                  <Bot className="w-6 h-6 text-purple-600 flex-shrink-0" />
                  <div>
                    <p className="text-sm text-gray-500 mb-1">AI Question</p>
                    <p className="text-gray-800">{item.question}</p>
                  </div>
                </div>
              </div>
              <div className="card bg-white ml-8">
                <p className="text-sm text-gray-500 mb-1">Your Answer</p>
                <p className="text-gray-800 mb-3">{item.answer}</p>
                {item.insight && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <p className="text-sm text-green-800">
                      <Sparkles className="w-4 h-4 inline mr-1" />
                      {item.insight}
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Current Question */}
          {questionNumber <= totalQuestions && (
            <div className="card bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-300">
              <div className="flex gap-3 mb-4">
                <Bot className="w-8 h-8 text-purple-600 flex-shrink-0" />
                <div>
                  <p className="text-sm text-purple-600 font-semibold mb-2">AI asks:</p>
                  <p className="text-lg text-gray-800">{currentQuestion}</p>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="mt-6">
                <textarea
                  className="w-full input-field min-h-32 resize-none"
                  placeholder="Type your authentic response here..."
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  rows={4}
                />
                <div className="flex justify-end mt-4">
                  <button type="submit" className="btn-primary" disabled={!answer.trim()}>
                    <Send className="w-5 h-5 inline mr-2" />
                    Submit Answer
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Completion */}
          {questionNumber > totalQuestions && (
            <div className="card text-center py-12 bg-gradient-to-br from-green-50 to-blue-50">
              <Sparkles className="w-16 h-16 text-green-600 mx-auto mb-4" />
              <h2 className="text-3xl font-bold text-gray-800 mb-4">Great job!</h2>
              <p className="text-gray-600 mb-6">
                You've completed the AI-mediated conversation. We're analyzing your responses and
                comparing them with your match's answers to assess compatibility.
              </p>
              <div className="bg-white rounded-lg p-6 max-w-md mx-auto">
                <p className="text-sm text-gray-500 mb-2">Next Steps:</p>
                <ol className="text-left text-gray-700 space-y-2">
                  <li>✓ Wait for your match to complete their questions</li>
                  <li>✓ AI will generate a compatibility report</li>
                  <li>✓ If compatible, you'll be able to start direct messaging</li>
                </ol>
              </div>
              <Link to="/matches" className="btn-primary mt-6 inline-block">
                Back to Matches
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
