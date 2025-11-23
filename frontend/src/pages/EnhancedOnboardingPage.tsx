/**
 * Enhanced Animated Onboarding Page
 * Complete profile setup with psychological assessment
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  User, Heart, Brain, MessageCircle, Target, Sparkles,
  CheckCircle, Camera, MapPin, Calendar
} from 'lucide-react';
import QuestionnaireQuestion from '../components/QuestionnaireQuestion';
import { questionSections, calculateTraitScore, allQuestions } from '../data/questionnaireData';

type Step = 'welcome' | 'basic-info' | 'photos' | 'questionnaire' | 'interests' | 'complete';

export default function EnhancedOnboardingPage() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<Step>('welcome');
  const [gender, setGender] = useState<'male' | 'female' | ''>('');

  // Form data
  const [basicInfo, setBasicInfo] = useState({
    firstName: '',
    lastName: '',
    dateOfBirth: '',
    gender: '',
    bio: '',
    city: '',
    country: '',
    lookingForGender: [] as string[],
    ageMin: 18,
    ageMax: 35,
    relationshipGoal: '',
  });

  const [questionnaireAnswers, setQuestionnaireAnswers] = useState<Record<string, any>>({});
  const [currentSection, setCurrentSection] = useState(0);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);

  const accentColor = gender === 'female' ? 'accent' : 'primary';

  // Progress calculation
  const totalSteps = 6;
  const stepProgress = {
    'welcome': 0,
    'basic-info': 1,
    'photos': 2,
    'questionnaire': 3,
    'interests': 4,
    'complete': 5,
  };
  const progress = (stepProgress[currentStep] / totalSteps) * 100;

  // Current question
  const currentSectionData = questionSections[currentSection];
  const currentQuestion = currentSectionData?.questions[currentQuestionIndex];

  const handleAnswer = (answer: any) => {
    if (currentQuestion) {
      setQuestionnaireAnswers(prev => ({
        ...prev,
        [currentQuestion.id]: answer,
      }));

      // Auto-advance after answering (except for text questions)
      if (currentQuestion.type !== 'text') {
        setTimeout(() => handleNextQuestion(), 300);
      }
    }
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < currentSectionData.questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    } else if (currentSection < questionSections.length - 1) {
      setCurrentSection(currentSection + 1);
      setCurrentQuestionIndex(0);
    } else {
      setCurrentStep('interests');
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    } else if (currentSection > 0) {
      setCurrentSection(currentSection - 1);
      setCurrentQuestionIndex(questionSections[currentSection - 1].questions.length - 1);
    }
  };

  const canProceedBasicInfo = basicInfo.firstName && basicInfo.gender && basicInfo.dateOfBirth;
  const canProceedQuestion = questionnaireAnswers[currentQuestion?.id] !== undefined;

  return (
    <div className={`min-h-screen ${
      gender === 'female'
        ? 'bg-gradient-to-br from-accent-50 via-white to-calm-50'
        : 'bg-gradient-to-br from-calm-50 via-white to-primary-50'
    }`}>
      {/* Progress Bar */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-white shadow-sm">
        <div className="h-2">
          <motion.div
            className={gender === 'female'
              ? 'h-full bg-gradient-to-r from-accent-400 to-accent-600'
              : 'h-full bg-gradient-to-r from-primary-400 to-primary-600'
            }
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      <div className="container mx-auto px-4 py-12 pt-20 max-w-4xl">
        <AnimatePresence mode="wait">
          {/* Welcome Screen */}
          {currentStep === 'welcome' && (
            <motion.div
              key="welcome"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.1 }}
              transition={{ duration: 0.5 }}
              className="text-center py-12"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: 'spring' }}
                className="mb-8"
              >
                <Heart className="w-24 h-24 mx-auto text-primary-500 mb-4" fill="currentColor" />
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-5xl font-bold text-gray-800 mb-4"
              >
                Welcome to DateNow
              </motion.h1>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto"
              >
                Let's create your profile and find meaningful connections through AI-guided compatibility
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="grid md:grid-cols-3 gap-6 mb-12"
              >
                <InfoCard
                  icon={<User className="w-8 h-8" />}
                  title="Your Profile"
                  description="Tell us about yourself"
                  delay={0.6}
                />
                <InfoCard
                  icon={<Brain className="w-8 h-8" />}
                  title="Personality"
                  description="Science-based assessment"
                  delay={0.7}
                />
                <InfoCard
                  icon={<Sparkles className="w-8 h-8" />}
                  title="Find Matches"
                  description="AI-powered compatibility"
                  delay={0.8}
                />
              </motion.div>

              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.9 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setCurrentStep('basic-info')}
                className="bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white font-semibold py-4 px-12 rounded-full text-lg shadow-lg transition-all"
              >
                Let's Get Started
              </motion.button>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
                className="text-sm text-gray-500 mt-6"
              >
                ⏱️ Takes about 15-20 minutes
              </motion.p>
            </motion.div>
          )}

          {/* Basic Info */}
          {currentStep === 'basic-info' && (
            <motion.div
              key="basic-info"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              transition={{ duration: 0.4 }}
              className="card max-w-2xl mx-auto"
            >
              <div className="text-center mb-8">
                <User className={`w-16 h-16 mx-auto mb-4 ${
                  gender === 'female' ? 'text-accent-500' : 'text-primary-500'
                }`} />
                <h2 className="text-3xl font-bold text-gray-800 mb-2">
                  About You
                </h2>
                <p className="text-gray-600">Let's start with the basics</p>
              </div>

              <div className="space-y-6">
                {/* Name */}
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      First Name *
                    </label>
                    <input
                      type="text"
                      value={basicInfo.firstName}
                      onChange={(e) => setBasicInfo({...basicInfo, firstName: e.target.value})}
                      className="input-field"
                      placeholder="John"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Last Name
                    </label>
                    <input
                      type="text"
                      value={basicInfo.lastName}
                      onChange={(e) => setBasicInfo({...basicInfo, lastName: e.target.value})}
                      className="input-field"
                      placeholder="Doe"
                    />
                  </div>
                </div>

                {/* Date of Birth */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    <Calendar className="w-4 h-4 inline mr-2" />
                    Date of Birth *
                  </label>
                  <input
                    type="date"
                    value={basicInfo.dateOfBirth}
                    onChange={(e) => setBasicInfo({...basicInfo, dateOfBirth: e.target.value})}
                    className="input-field"
                    max={new Date(new Date().setFullYear(new Date().getFullYear() - 18)).toISOString().split('T')[0]}
                  />
                </div>

                {/* Gender */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    I am *
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    {['Male', 'Female'].map((g) => (
                      <motion.button
                        key={g}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={() => {
                          setBasicInfo({...basicInfo, gender: g.toLowerCase()});
                          setGender(g.toLowerCase() as 'male' | 'female');
                        }}
                        className={`
                          py-4 px-6 rounded-xl font-semibold transition-all
                          ${basicInfo.gender === g.toLowerCase()
                            ? g === 'Female'
                              ? 'bg-gradient-to-r from-accent-400 to-accent-600 text-white shadow-lg'
                              : 'bg-gradient-to-r from-primary-400 to-primary-600 text-white shadow-lg'
                            : 'bg-white text-gray-700 hover:bg-gray-50 shadow-md'
                          }
                        `}
                      >
                        {g}
                      </motion.button>
                    ))}
                  </div>
                </div>

                {/* Looking For */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Looking for
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    {['Male', 'Female'].map((g) => {
                      const selected = basicInfo.lookingForGender.includes(g.toLowerCase());
                      return (
                        <motion.button
                          key={g}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => {
                            const newLooking = selected
                              ? basicInfo.lookingForGender.filter(x => x !== g.toLowerCase())
                              : [...basicInfo.lookingForGender, g.toLowerCase()];
                            setBasicInfo({...basicInfo, lookingForGender: newLooking});
                          }}
                          className={`
                            py-4 px-6 rounded-xl font-semibold transition-all
                            ${selected
                              ? gender === 'female'
                                ? 'bg-gradient-to-r from-accent-400 to-accent-600 text-white shadow-lg'
                                : 'bg-gradient-to-r from-primary-400 to-primary-600 text-white shadow-lg'
                              : 'bg-white text-gray-700 hover:bg-gray-50 shadow-md'
                            }
                          `}
                        >
                          {g}
                        </motion.button>
                      );
                    })}
                  </div>
                </div>

                {/* Location */}
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      <MapPin className="w-4 h-4 inline mr-2" />
                      City
                    </label>
                    <input
                      type="text"
                      value={basicInfo.city}
                      onChange={(e) => setBasicInfo({...basicInfo, city: e.target.value})}
                      className="input-field"
                      placeholder="New York"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Country
                    </label>
                    <input
                      type="text"
                      value={basicInfo.country}
                      onChange={(e) => setBasicInfo({...basicInfo, country: e.target.value})}
                      className="input-field"
                      placeholder="United States"
                    />
                  </div>
                </div>

                {/* Bio */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    About Me
                  </label>
                  <textarea
                    value={basicInfo.bio}
                    onChange={(e) => setBasicInfo({...basicInfo, bio: e.target.value})}
                    className="input-field resize-none"
                    rows={4}
                    placeholder="Tell us about yourself..."
                  />
                </div>
              </div>

              <div className="flex gap-4 mt-8">
                <button
                  onClick={() => setCurrentStep('welcome')}
                  className="btn-secondary flex-1"
                >
                  Back
                </button>
                <button
                  onClick={() => setCurrentStep('photos')}
                  disabled={!canProceedBasicInfo}
                  className="btn-primary flex-1 disabled:opacity-50"
                >
                  Continue
                </button>
              </div>
            </motion.div>
          )}

          {/* Photos Step */}
          {currentStep === 'photos' && (
            <motion.div
              key="photos"
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -50 }}
              className="card max-w-2xl mx-auto"
            >
              <div className="text-center mb-8">
                <Camera className={`w-16 h-16 mx-auto mb-4 ${
                  gender === 'female' ? 'text-accent-500' : 'text-primary-500'
                }`} />
                <h2 className="text-3xl font-bold text-gray-800 mb-2">
                  Add Photos
                </h2>
                <p className="text-gray-600">Show your authentic self</p>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-8">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.1 }}
                    whileHover={{ scale: 1.05 }}
                    className={`
                      aspect-square rounded-xl border-2 border-dashed flex items-center justify-center cursor-pointer transition-all
                      ${gender === 'female'
                        ? 'border-accent-300 hover:border-accent-500 hover:bg-accent-50'
                        : 'border-primary-300 hover:border-primary-500 hover:bg-primary-50'
                      }
                    `}
                  >
                    <Camera className={`w-8 h-8 ${
                      gender === 'female' ? 'text-accent-400' : 'text-primary-400'
                    }`} />
                  </motion.div>
                ))}
              </div>

              <p className="text-sm text-gray-600 text-center mb-8">
                📸 Add at least 2 photos to continue. Pro tip: Smile and show your hobbies!
              </p>

              <div className="flex gap-4">
                <button
                  onClick={() => setCurrentStep('basic-info')}
                  className="btn-secondary flex-1"
                >
                  Back
                </button>
                <button
                  onClick={() => setCurrentStep('questionnaire')}
                  className="btn-primary flex-1"
                >
                  Continue
                </button>
              </div>
            </motion.div>
          )}

          {/* Questionnaire */}
          {currentStep === 'questionnaire' && currentQuestion && (
            <motion.div
              key="questionnaire"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="max-w-3xl mx-auto"
            >
              {/* Section Header */}
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center mb-8"
              >
                <div className="text-6xl mb-4">{currentSectionData.icon}</div>
                <h2 className="text-3xl font-bold text-gray-800 mb-2">
                  {currentSectionData.title}
                </h2>
                <p className="text-gray-600 mb-4">{currentSectionData.description}</p>
                <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                  <span>Question {currentQuestionIndex + 1} of {currentSectionData.questions.length}</span>
                  <span>•</span>
                  <span>{currentSectionData.estimatedTime}</span>
                </div>
              </motion.div>

              {/* Progress Dots */}
              <div className="flex justify-center gap-2 mb-8">
                {currentSectionData.questions.map((_, i) => (
                  <motion.div
                    key={i}
                    className={`h-2 rounded-full transition-all ${
                      i === currentQuestionIndex
                        ? gender === 'female'
                          ? 'w-8 bg-accent-500'
                          : 'w-8 bg-primary-500'
                        : i < currentQuestionIndex
                          ? gender === 'female'
                            ? 'w-2 bg-accent-300'
                            : 'w-2 bg-primary-300'
                          : 'w-2 bg-gray-300'
                    }`}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: i * 0.02 }}
                  />
                ))}
              </div>

              {/* Question Card */}
              <div className="card">
                <QuestionnaireQuestion
                  question={currentQuestion}
                  answer={questionnaireAnswers[currentQuestion.id]}
                  onAnswer={handleAnswer}
                  gender={gender as 'male' | 'female'}
                />

                <div className="flex gap-4 mt-8">
                  <button
                    onClick={handlePreviousQuestion}
                    disabled={currentSection === 0 && currentQuestionIndex === 0}
                    className="btn-secondary flex-1 disabled:opacity-50"
                  >
                    Back
                  </button>
                  <button
                    onClick={handleNextQuestion}
                    disabled={!canProceedQuestion}
                    className="btn-primary flex-1 disabled:opacity-50"
                  >
                    {currentSection === questionSections.length - 1 &&
                     currentQuestionIndex === currentSectionData.questions.length - 1
                      ? 'Finish'
                      : 'Next'
                    }
                  </button>
                </div>
              </div>

              {/* Section Progress */}
              <div className="mt-8 text-center">
                <p className="text-sm text-gray-500">
                  Section {currentSection + 1} of {questionSections.length}
                </p>
              </div>
            </motion.div>
          )}

          {/* Complete */}
          {currentStep === 'complete' && (
            <motion.div
              key="complete"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center py-12"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: [0, 1.2, 1] }}
                transition={{ duration: 0.5 }}
              >
                <CheckCircle className={`w-32 h-32 mx-auto mb-8 ${
                  gender === 'female' ? 'text-accent-500' : 'text-primary-500'
                }`} />
              </motion.div>

              <h2 className="text-4xl font-bold text-gray-800 mb-4">
                You're All Set, {basicInfo.firstName}!
              </h2>
              <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
                Your profile is complete. Our AI is now finding compatible matches based on your personality and preferences.
              </p>

              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => navigate('/dashboard')}
                className={`
                  ${gender === 'female'
                    ? 'bg-gradient-to-r from-accent-500 to-accent-600 hover:from-accent-600 hover:to-accent-700'
                    : 'bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700'
                  }
                  text-white font-semibold py-4 px-12 rounded-full text-lg shadow-lg
                `}
              >
                Find My Matches
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function InfoCard({ icon, title, description, delay }: any) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="card hover:shadow-xl transition-shadow"
    >
      <div className="text-primary-500 mb-3">{icon}</div>
      <h3 className="font-semibold text-gray-800 mb-1">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </motion.div>
  );
}
