/**
 * Comprehensive Psychological Questionnaire Data
 * Science-based questions for personality, values, and compatibility assessment
 */

export interface Question {
  id: string;
  text: string;
  type: 'scale' | 'multiple_choice' | 'single_choice' | 'text';
  category: string;
  options?: string[];
  reverse?: boolean; // For reverse-scored items
  trait?: string; // Which trait this measures
}

// Big Five Personality Traits Questions (44 items - validated BFI-44)
export const bigFiveQuestions: Question[] = [
  // Extraversion
  { id: 'bf_1', text: 'I am the life of the party', type: 'scale', category: 'personality', trait: 'extraversion' },
  { id: 'bf_2', text: "I don't talk a lot", type: 'scale', category: 'personality', trait: 'extraversion', reverse: true },
  { id: 'bf_3', text: 'I feel comfortable around people', type: 'scale', category: 'personality', trait: 'extraversion' },
  { id: 'bf_4', text: 'I keep in the background', type: 'scale', category: 'personality', trait: 'extraversion', reverse: true },
  { id: 'bf_5', text: 'I start conversations', type: 'scale', category: 'personality', trait: 'extraversion' },
  { id: 'bf_6', text: 'I have little to say', type: 'scale', category: 'personality', trait: 'extraversion', reverse: true },
  { id: 'bf_7', text: 'I talk to a lot of different people at parties', type: 'scale', category: 'personality', trait: 'extraversion' },
  { id: 'bf_8', text: "I don't like to draw attention to myself", type: 'scale', category: 'personality', trait: 'extraversion', reverse: true },

  // Agreeableness
  { id: 'bf_9', text: 'I feel little concern for others', type: 'scale', category: 'personality', trait: 'agreeableness', reverse: true },
  { id: 'bf_10', text: 'I am interested in people', type: 'scale', category: 'personality', trait: 'agreeableness' },
  { id: 'bf_11', text: 'I insult people', type: 'scale', category: 'personality', trait: 'agreeableness', reverse: true },
  { id: 'bf_12', text: "I sympathize with others' feelings", type: 'scale', category: 'personality', trait: 'agreeableness' },
  { id: 'bf_13', text: "I am not interested in other people's problems", type: 'scale', category: 'personality', trait: 'agreeableness', reverse: true },
  { id: 'bf_14', text: 'I have a soft heart', type: 'scale', category: 'personality', trait: 'agreeableness' },
  { id: 'bf_15', text: 'I am not really interested in others', type: 'scale', category: 'personality', trait: 'agreeableness', reverse: true },
  { id: 'bf_16', text: 'I take time out for others', type: 'scale', category: 'personality', trait: 'agreeableness' },
  { id: 'bf_17', text: "I feel others' emotions", type: 'scale', category: 'personality', trait: 'agreeableness' },
  { id: 'bf_18', text: 'I make people feel at ease', type: 'scale', category: 'personality', trait: 'agreeableness' },

  // Conscientiousness
  { id: 'bf_19', text: 'I am always prepared', type: 'scale', category: 'personality', trait: 'conscientiousness' },
  { id: 'bf_20', text: 'I leave my belongings around', type: 'scale', category: 'personality', trait: 'conscientiousness', reverse: true },
  { id: 'bf_21', text: 'I pay attention to details', type: 'scale', category: 'personality', trait: 'conscientiousness' },
  { id: 'bf_22', text: 'I make a mess of things', type: 'scale', category: 'personality', trait: 'conscientiousness', reverse: true },
  { id: 'bf_23', text: 'I get chores done right away', type: 'scale', category: 'personality', trait: 'conscientiousness' },
  { id: 'bf_24', text: 'I often forget to put things back in their proper place', type: 'scale', category: 'personality', trait: 'conscientiousness', reverse: true },
  { id: 'bf_25', text: 'I like order', type: 'scale', category: 'personality', trait: 'conscientiousness' },
  { id: 'bf_26', text: 'I shirk my duties', type: 'scale', category: 'personality', trait: 'conscientiousness', reverse: true },
  { id: 'bf_27', text: 'I follow a schedule', type: 'scale', category: 'personality', trait: 'conscientiousness' },
  { id: 'bf_28', text: 'I am exacting in my work', type: 'scale', category: 'personality', trait: 'conscientiousness' },

  // Neuroticism (Emotional Stability)
  { id: 'bf_29', text: 'I get stressed out easily', type: 'scale', category: 'personality', trait: 'neuroticism' },
  { id: 'bf_30', text: 'I am relaxed most of the time', type: 'scale', category: 'personality', trait: 'neuroticism', reverse: true },
  { id: 'bf_31', text: 'I worry about things', type: 'scale', category: 'personality', trait: 'neuroticism' },
  { id: 'bf_32', text: 'I seldom feel blue', type: 'scale', category: 'personality', trait: 'neuroticism', reverse: true },
  { id: 'bf_33', text: 'I am easily disturbed', type: 'scale', category: 'personality', trait: 'neuroticism' },
  { id: 'bf_34', text: 'I get upset easily', type: 'scale', category: 'personality', trait: 'neuroticism' },
  { id: 'bf_35', text: 'I change my mood a lot', type: 'scale', category: 'personality', trait: 'neuroticism' },
  { id: 'bf_36', text: 'I have frequent mood swings', type: 'scale', category: 'personality', trait: 'neuroticism' },

  // Openness to Experience
  { id: 'bf_37', text: 'I have a rich vocabulary', type: 'scale', category: 'personality', trait: 'openness' },
  { id: 'bf_38', text: 'I have difficulty understanding abstract ideas', type: 'scale', category: 'personality', trait: 'openness', reverse: true },
  { id: 'bf_39', text: 'I have a vivid imagination', type: 'scale', category: 'personality', trait: 'openness' },
  { id: 'bf_40', text: 'I am not interested in abstract ideas', type: 'scale', category: 'personality', trait: 'openness', reverse: true },
  { id: 'bf_41', text: 'I have excellent ideas', type: 'scale', category: 'personality', trait: 'openness' },
  { id: 'bf_42', text: 'I do not have a good imagination', type: 'scale', category: 'personality', trait: 'openness', reverse: true },
  { id: 'bf_43', text: 'I am quick to understand things', type: 'scale', category: 'personality', trait: 'openness' },
  { id: 'bf_44', text: 'I spend time reflecting on things', type: 'scale', category: 'personality', trait: 'openness' },
];

// Core Values Questions
export const valuesQuestions: Question[] = [
  {
    id: 'val_1',
    text: 'How important is having a family in your future?',
    type: 'scale',
    category: 'values',
    trait: 'family_orientation',
  },
  {
    id: 'val_2',
    text: 'How important is career success and professional achievement to you?',
    type: 'scale',
    category: 'values',
    trait: 'career_ambition',
  },
  {
    id: 'val_3',
    text: 'How much do you value adventure and new experiences?',
    type: 'scale',
    category: 'values',
    trait: 'adventure_seeking',
  },
  {
    id: 'val_4',
    text: 'How important is making a positive impact on society?',
    type: 'scale',
    category: 'values',
    trait: 'social_consciousness',
  },
  {
    id: 'val_5',
    text: 'How important is spirituality or religion in your life?',
    type: 'scale',
    category: 'values',
    trait: 'spiritual_religious',
  },
  {
    id: 'val_6',
    text: 'I prefer to have children:',
    type: 'single_choice',
    category: 'values',
    trait: 'family_orientation',
    options: ['Definitely', 'Probably', 'Not sure', 'Probably not', 'Definitely not'],
  },
  {
    id: 'val_7',
    text: 'My ideal weekend involves:',
    type: 'single_choice',
    category: 'values',
    trait: 'lifestyle',
    options: [
      'Outdoor adventures and activities',
      'Cultural events and entertainment',
      'Relaxing at home with loved ones',
      'Social gatherings with friends',
      'Working on personal projects',
    ],
  },
];

// Love Languages Questions
export const loveLangaugesQuestions: Question[] = [
  {
    id: 'll_1',
    text: 'I feel most loved when my partner tells me they appreciate me',
    type: 'scale',
    category: 'love_languages',
    trait: 'love_language_words',
  },
  {
    id: 'll_2',
    text: 'I feel most loved when my partner does thoughtful things for me',
    type: 'scale',
    category: 'love_languages',
    trait: 'love_language_acts',
  },
  {
    id: 'll_3',
    text: 'I feel most loved when my partner gives me meaningful gifts',
    type: 'scale',
    category: 'love_languages',
    trait: 'love_language_gifts',
  },
  {
    id: 'll_4',
    text: 'I feel most loved when my partner spends quality time with me',
    type: 'scale',
    category: 'love_languages',
    trait: 'love_language_time',
  },
  {
    id: 'll_5',
    text: 'I feel most loved through physical touch and affection',
    type: 'scale',
    category: 'love_languages',
    trait: 'love_language_touch',
  },
];

// Communication Style Questions
export const communicationQuestions: Question[] = [
  {
    id: 'comm_1',
    text: 'How do you prefer to communicate?',
    type: 'single_choice',
    category: 'communication',
    trait: 'communication_style',
    options: [
      'Direct and straightforward',
      'Diplomatic and tactful',
      'Emotional and expressive',
      'Logical and analytical',
    ],
  },
  {
    id: 'comm_2',
    text: 'When there is conflict, I tend to:',
    type: 'single_choice',
    category: 'communication',
    trait: 'conflict_resolution',
    options: [
      'Address it directly and immediately',
      'Take time to cool down first',
      'Seek compromise and middle ground',
      'Avoid confrontation when possible',
    ],
  },
  {
    id: 'comm_3',
    text: 'I prefer to resolve disagreements by:',
    type: 'single_choice',
    category: 'communication',
    trait: 'conflict_resolution',
    options: [
      'Working together to find solutions',
      'Taking turns getting our way',
      'Having deep discussions about feelings',
      'Giving each other space then reconnecting',
    ],
  },
];

// Attachment Style Questions
export const attachmentQuestions: Question[] = [
  {
    id: 'att_1',
    text: 'I find it easy to get emotionally close to others',
    type: 'scale',
    category: 'attachment',
    trait: 'attachment_style',
  },
  {
    id: 'att_2',
    text: 'I worry about being abandoned in relationships',
    type: 'scale',
    category: 'attachment',
    trait: 'attachment_style',
  },
  {
    id: 'att_3',
    text: 'I am comfortable depending on others',
    type: 'scale',
    category: 'attachment',
    trait: 'attachment_style',
  },
  {
    id: 'att_4',
    text: 'I worry that others will not value me as much as I value them',
    type: 'scale',
    category: 'attachment',
    trait: 'attachment_style',
  },
  {
    id: 'att_5',
    text: 'In relationships, I prefer to:',
    type: 'single_choice',
    category: 'attachment',
    trait: 'attachment_style',
    options: [
      'Be very close and connected',
      'Maintain some independence',
      'Keep emotional distance',
      'It depends on the situation',
    ],
  },
];

// Relationship Goals
export const relationshipGoalsQuestions: Question[] = [
  {
    id: 'rg_1',
    text: 'What are you looking for?',
    type: 'single_choice',
    category: 'goals',
    trait: 'relationship_goal',
    options: [
      'A serious, long-term relationship',
      'Dating to see where it goes',
      'Casual dating',
      'New friends and connections',
    ],
  },
  {
    id: 'rg_2',
    text: 'How soon do you see yourself settling down?',
    type: 'single_choice',
    category: 'goals',
    trait: 'timeline',
    options: [
      'Ready now',
      'Within the next year',
      'In a few years',
      'Not sure yet',
      'Not looking to settle down',
    ],
  },
];

// Deal Breakers & Preferences
export const preferencesQuestions: Question[] = [
  {
    id: 'pref_1',
    text: 'How important is physical attraction to you?',
    type: 'scale',
    category: 'preferences',
    trait: 'physical_importance',
  },
  {
    id: 'pref_2',
    text: 'How important is it that your partner shares your religious/spiritual beliefs?',
    type: 'scale',
    category: 'preferences',
    trait: 'spiritual_match',
  },
  {
    id: 'pref_3',
    text: 'How important is intellectual compatibility?',
    type: 'scale',
    category: 'preferences',
    trait: 'intellectual_match',
  },
  {
    id: 'pref_4',
    text: 'Your partner smoking is:',
    type: 'single_choice',
    category: 'preferences',
    trait: 'smoking',
    options: ['A deal breaker', 'A concern', 'Not ideal but okay', 'Not an issue'],
  },
  {
    id: 'pref_5',
    text: 'How often do you drink alcohol?',
    type: 'single_choice',
    category: 'preferences',
    trait: 'drinking',
    options: ['Never', 'Rarely', 'Socially', 'Regularly', 'Prefer not to say'],
  },
];

// Anti-Bot Verification Questions
export const verificationQuestions: Question[] = [
  {
    id: 'verify_1',
    text: 'What brings you to DateNow? (Genuine answer required)',
    type: 'text',
    category: 'verification',
    trait: 'authenticity',
  },
  {
    id: 'verify_2',
    text: 'Describe your ideal first date in your own words',
    type: 'text',
    category: 'verification',
    trait: 'authenticity',
  },
];

// All questions combined
export const allQuestions = {
  bigFive: bigFiveQuestions,
  values: valuesQuestions,
  loveLanguages: loveLangaugesQuestions,
  communication: communicationQuestions,
  attachment: attachmentQuestions,
  relationshipGoals: relationshipGoalsQuestions,
  preferences: preferencesQuestions,
  verification: verificationQuestions,
};

// Question sections for onboarding flow
export const questionSections = [
  {
    id: 'personality',
    title: 'Your Personality',
    description: 'Help us understand who you are',
    icon: '🧠',
    questions: bigFiveQuestions,
    estimatedTime: '5-7 min',
  },
  {
    id: 'values',
    title: 'Your Values',
    description: 'What matters most to you in life',
    icon: '💎',
    questions: valuesQuestions,
    estimatedTime: '2-3 min',
  },
  {
    id: 'love',
    title: 'Love & Connection',
    description: 'How you give and receive love',
    icon: '💕',
    questions: loveLangaugesQuestions,
    estimatedTime: '2 min',
  },
  {
    id: 'communication',
    title: 'Communication Style',
    description: 'How you express yourself',
    icon: '💬',
    questions: communicationQuestions,
    estimatedTime: '2 min',
  },
  {
    id: 'attachment',
    title: 'Attachment & Bonding',
    description: 'Your relationship patterns',
    icon: '🤝',
    questions: attachmentQuestions,
    estimatedTime: '2 min',
  },
  {
    id: 'goals',
    title: 'Relationship Goals',
    description: 'What you are looking for',
    icon: '🎯',
    questions: relationshipGoalsQuestions,
    estimatedTime: '1 min',
  },
  {
    id: 'preferences',
    title: 'Preferences & Deal-Breakers',
    description: 'What is important to you',
    icon: '✨',
    questions: preferencesQuestions,
    estimatedTime: '2 min',
  },
  {
    id: 'verification',
    title: 'Verification',
    description: 'Prove you are a real person',
    icon: '✅',
    questions: verificationQuestions,
    estimatedTime: '1 min',
  },
];

// Scale labels
export const scaleLabels = {
  1: 'Strongly Disagree',
  2: 'Disagree',
  3: 'Neutral',
  4: 'Agree',
  5: 'Strongly Agree',
};

// Calculate scores helper
export function calculateTraitScore(answers: Record<string, number>, trait: string, questions: Question[]): number {
  const relevantQuestions = questions.filter(q => q.trait === trait);
  let sum = 0;
  let count = 0;

  relevantQuestions.forEach(q => {
    if (answers[q.id] !== undefined) {
      const score = q.reverse ? (6 - answers[q.id]) : answers[q.id];
      sum += score;
      count++;
    }
  });

  return count > 0 ? (sum / count / 5) * 100 : 0; // Convert to 0-100 scale
}
