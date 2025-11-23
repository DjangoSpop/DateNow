/**
 * Onboarding Page - Complete profile and psychological assessment
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Heart, User, Brain, CheckCircle } from 'lucide-react';

export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const navigate = useNavigate();

  const completeOnboarding = () => {
    navigate('/dashboard');
  };

  return (
    <div className="min-h-screen py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Progress Steps */}
        <div className="flex justify-center items-center mb-12">
          <StepIndicator number={1} label="Profile" active={step === 1} completed={step > 1} />
          <div className="w-24 h-1 bg-gray-300 mx-2" />
          <StepIndicator number={2} label="Assessment" active={step === 2} completed={step > 2} />
          <div className="w-24 h-1 bg-gray-300 mx-2" />
          <StepIndicator number={3} label="Preferences" active={step === 3} completed={step > 3} />
        </div>

        {/* Content */}
        <div className="card max-w-2xl mx-auto">
          {step === 1 && (
            <div className="text-center py-8">
              <User className="w-16 h-16 text-pink-600 mx-auto mb-6" />
              <h2 className="text-3xl font-bold mb-4 text-gray-800">Complete Your Profile</h2>
              <p className="text-gray-600 mb-8">
                Tell us about yourself so we can find the best matches for you.
              </p>
              <div className="space-y-4 text-left">
                <p className="text-sm text-gray-500">This is where profile form fields would go:</p>
                <ul className="list-disc list-inside text-gray-600 space-y-2">
                  <li>Basic info (age, location, gender)</li>
                  <li>Bio and interests</li>
                  <li>Photos</li>
                  <li>Relationship goals</li>
                </ul>
              </div>
              <button onClick={() => setStep(2)} className="btn-primary mt-8">
                Continue to Assessment
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="text-center py-8">
              <Brain className="w-16 h-16 text-purple-600 mx-auto mb-6" />
              <h2 className="text-3xl font-bold mb-4 text-gray-800">Psychological Assessment</h2>
              <p className="text-gray-600 mb-8">
                Answer questions about your personality, values, and communication style.
              </p>
              <div className="space-y-4 text-left">
                <p className="text-sm text-gray-500">Assessment would include:</p>
                <ul className="list-disc list-inside text-gray-600 space-y-2">
                  <li>Big Five Personality Traits</li>
                  <li>Core Values Assessment</li>
                  <li>Love Languages</li>
                  <li>Communication & Conflict Resolution Styles</li>
                  <li>Attachment Style</li>
                </ul>
              </div>
              <button onClick={() => setStep(3)} className="btn-primary mt-8">
                Continue to Preferences
              </button>
            </div>
          )}

          {step === 3 && (
            <div className="text-center py-8">
              <Heart className="w-16 h-16 text-pink-600 mx-auto mb-6" fill="currentColor" />
              <h2 className="text-3xl font-bold mb-4 text-gray-800">Match Preferences</h2>
              <p className="text-gray-600 mb-8">
                Set your preferences for potential matches.
              </p>
              <div className="space-y-4 text-left">
                <p className="text-sm text-gray-500">Preferences include:</p>
                <ul className="list-disc list-inside text-gray-600 space-y-2">
                  <li>Gender preferences</li>
                  <li>Age range</li>
                  <li>Distance preferences</li>
                  <li>Deal breakers and must-haves</li>
                </ul>
              </div>
              <button onClick={completeOnboarding} className="btn-primary mt-8">
                Complete Setup
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StepIndicator({ number, label, active, completed }: { number: number; label: string; active: boolean; completed: boolean }) {
  return (
    <div className="flex flex-col items-center">
      <div
        className={`w-12 h-12 rounded-full flex items-center justify-center font-bold ${
          completed
            ? 'bg-green-500 text-white'
            : active
            ? 'bg-pink-600 text-white'
            : 'bg-gray-300 text-gray-600'
        }`}
      >
        {completed ? <CheckCircle className="w-6 h-6" /> : number}
      </div>
      <span className="text-sm mt-2 text-gray-600">{label}</span>
    </div>
  );
}
