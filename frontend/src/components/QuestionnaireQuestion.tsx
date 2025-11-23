/**
 * Animated Questionnaire Question Component
 */
import { motion } from 'framer-motion';
import { Question, scaleLabels } from '../data/questionnaireData';

interface Props {
  question: Question;
  answer: any;
  onAnswer: (answer: any) => void;
  gender?: 'male' | 'female';
}

export default function QuestionnaireQuestion({ question, answer, onAnswer, gender }: Props) {
  const accentColor = gender === 'female' ? 'accent' : 'primary';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      {/* Question Text */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="text-center"
      >
        <h3 className="text-2xl font-semibold text-gray-800 mb-2">
          {question.text}
        </h3>
      </motion.div>

      {/* Scale Type */}
      {question.type === 'scale' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center gap-2">
            {[1, 2, 3, 4, 5].map((value) => (
              <motion.button
                key={value}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => onAnswer(value)}
                className={`
                  flex-1 py-6 px-4 rounded-xl font-semibold transition-all duration-300
                  ${answer === value
                    ? gender === 'female'
                      ? 'bg-gradient-to-br from-accent-400 to-accent-600 text-white shadow-lg scale-105'
                      : 'bg-gradient-to-br from-primary-400 to-primary-600 text-white shadow-lg scale-105'
                    : 'bg-white text-gray-600 hover:bg-gray-50 shadow-md'
                  }
                `}
              >
                <div className="text-3xl mb-2">{value}</div>
                <div className="text-xs">{scaleLabels[value as keyof typeof scaleLabels]}</div>
              </motion.button>
            ))}
          </div>

          {/* Labels */}
          <div className="flex justify-between text-sm text-gray-500 px-2">
            <span>Strongly Disagree</span>
            <span>Strongly Agree</span>
          </div>
        </div>
      )}

      {/* Single Choice */}
      {question.type === 'single_choice' && question.options && (
        <div className="space-y-3">
          {question.options.map((option, index) => (
            <motion.button
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onAnswer(option)}
              className={`
                w-full py-4 px-6 rounded-xl text-left font-medium transition-all duration-300
                ${answer === option
                  ? gender === 'female'
                    ? 'bg-gradient-to-r from-accent-400 to-accent-600 text-white shadow-lg'
                    : 'bg-gradient-to-r from-primary-400 to-primary-600 text-white shadow-lg'
                  : 'bg-white text-gray-700 hover:bg-gray-50 shadow-md'
                }
              `}
            >
              <div className="flex items-center">
                <div className={`
                  w-6 h-6 rounded-full border-2 mr-3 flex items-center justify-center
                  ${answer === option
                    ? 'border-white bg-white'
                    : gender === 'female'
                      ? 'border-accent-300'
                      : 'border-primary-300'
                  }
                `}>
                  {answer === option && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className={gender === 'female' ? 'w-3 h-3 rounded-full bg-accent-500' : 'w-3 h-3 rounded-full bg-primary-500'}
                    />
                  )}
                </div>
                <span>{option}</span>
              </div>
            </motion.button>
          ))}
        </div>
      )}

      {/* Multiple Choice */}
      {question.type === 'multiple_choice' && question.options && (
        <div className="space-y-3">
          {question.options.map((option, index) => {
            const selected = Array.isArray(answer) && answer.includes(option);
            return (
              <motion.button
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  const newAnswer = Array.isArray(answer) ? [...answer] : [];
                  if (selected) {
                    onAnswer(newAnswer.filter(a => a !== option));
                  } else {
                    onAnswer([...newAnswer, option]);
                  }
                }}
                className={`
                  w-full py-4 px-6 rounded-xl text-left font-medium transition-all duration-300
                  ${selected
                    ? gender === 'female'
                      ? 'bg-gradient-to-r from-accent-400 to-accent-600 text-white shadow-lg'
                      : 'bg-gradient-to-r from-primary-400 to-primary-600 text-white shadow-lg'
                    : 'bg-white text-gray-700 hover:bg-gray-50 shadow-md'
                  }
                `}
              >
                <div className="flex items-center">
                  <div className={`
                    w-6 h-6 rounded-md border-2 mr-3 flex items-center justify-center
                    ${selected
                      ? 'border-white bg-white'
                      : gender === 'female'
                        ? 'border-accent-300'
                        : 'border-primary-300'
                    }
                  `}>
                    {selected && (
                      <motion.svg
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: 1 }}
                        className="w-4 h-4"
                        viewBox="0 0 20 20"
                        fill="none"
                      >
                        <path
                          d="M6 10l3 3 6-6"
                          stroke={gender === 'female' ? '#eb2f96' : '#1677ff'}
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </motion.svg>
                    )}
                  </div>
                  <span>{option}</span>
                </div>
              </motion.button>
            );
          })}
        </div>
      )}

      {/* Text Input */}
      {question.type === 'text' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <textarea
            value={answer || ''}
            onChange={(e) => onAnswer(e.target.value)}
            placeholder="Type your answer here..."
            className={`
              w-full px-6 py-4 rounded-xl border-2 transition-all duration-300
              focus:outline-none focus:ring-2 resize-none
              ${gender === 'female'
                ? 'border-accent-200 focus:border-accent-400 focus:ring-accent-200'
                : 'border-primary-200 focus:border-primary-400 focus:ring-primary-200'
              }
            `}
            rows={6}
            minLength={20}
          />
          <p className="text-sm text-gray-500 mt-2">
            {answer?.length || 0} characters (minimum 20)
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}
