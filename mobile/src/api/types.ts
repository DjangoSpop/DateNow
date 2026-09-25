/**
 * Types mirroring docs/API_CONTRACT.md (Sprint 1). Keep in sync with the contract, not the backend code.
 */

export type Gender = 'male' | 'female' | 'non_binary' | 'other';
export const GENDERS: readonly Gender[] = ['male', 'female', 'non_binary', 'other'];

export type RelationshipGoal = 'serious' | 'casual' | 'friendship' | 'unsure';
export const RELATIONSHIP_GOALS: readonly RelationshipGoal[] = [
  'serious',
  'casual',
  'friendship',
  'unsure',
];

/** Stable error codes from the contract, plus client-side codes (last group). */
export type ApiErrorCode =
  | 'NOT_AUTHENTICATED'
  | 'INVALID_TOKEN'
  | 'TOKEN_EXPIRED'
  | 'INVALID_CREDENTIALS'
  | 'ACCOUNT_DISABLED'
  | 'NOT_FOUND'
  | 'PROFILE_NOT_FOUND'
  | 'PSYCH_PROFILE_NOT_FOUND'
  | 'EMAIL_TAKEN'
  | 'PROFILE_EXISTS'
  | 'VALIDATION_ERROR'
  | 'QUESTIONNAIRE_INCOMPLETE'
  | 'INTERNAL_ERROR'
  // client-side
  | 'NETWORK_ERROR'
  | 'TIMEOUT'
  | 'ABORTED'
  | 'INVALID_RESPONSE'
  | 'UNKNOWN_ERROR';

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    fields?: Record<string, string>;
  };
}

// ---- Auth ----
export interface Credentials {
  email: string;
  password: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
}

// ---- Current user ----
export interface Onboarding {
  profile_complete: boolean;
  questionnaire_complete: boolean;
  questionnaire_answered: number;
  questionnaire_total: number;
  questionnaire_version: string;
  complete: boolean;
}

export interface Me {
  id: number;
  email: string;
  is_verified: boolean;
  created_at: string;
  onboarding: Onboarding;
}

// ---- Profile ----
export interface ProfileCreate {
  first_name: string;
  last_name?: string | null;
  date_of_birth: string;
  gender: Gender;
  looking_for_gender: Gender[];
  age_preference_min: number;
  age_preference_max: number;
  relationship_goal: RelationshipGoal;
  bio?: string | null;
  city?: string | null;
  country?: string | null;
}

export type ProfileUpdate = Partial<ProfileCreate>;

export interface Profile {
  first_name: string;
  last_name: string | null;
  date_of_birth: string;
  age: number;
  gender: Gender;
  looking_for_gender: Gender[];
  age_preference_min: number;
  age_preference_max: number;
  relationship_goal: RelationshipGoal;
  bio: string | null;
  city: string | null;
  country: string | null;
  created_at: string;
  updated_at: string;
}

// ---- Questionnaire ----
export interface ScaleSpec {
  min: number;
  max: number;
  /** Keys are stringified scale values; not every value necessarily has a label. */
  labels: Record<string, string>;
}

export interface ChoiceOption {
  value: string;
  label: string;
}

interface QuestionBase {
  id: string;
  text: string;
  required: boolean;
}

export interface ScaleQuestion extends QuestionBase {
  type: 'scale';
  scale: ScaleSpec;
}

export interface SingleChoiceQuestion extends QuestionBase {
  type: 'single_choice';
  options: ChoiceOption[];
}

export type Question = ScaleQuestion | SingleChoiceQuestion;

export interface QuestionnaireSection {
  id: string;
  title: string;
  description: string;
  estimated_minutes: number;
  questions: Question[];
}

export interface Questionnaire {
  version: string;
  sections: QuestionnaireSection[];
}

export type AnswerValue = number | string;
export type Answers = Record<string, AnswerValue>;

export interface QuestionnaireState {
  version: string;
  answers: Answers;
  answered: number;
  total_required: number;
  missing: string[];
  complete: boolean;
  scored_at: string | null;
}

// ---- Psychological profile ----
export interface BigFive {
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
}

export interface PsychologicalProfile {
  questionnaire_version: string;
  scored_at: string;
  big_five: BigFive;
  values: Record<string, number>;
  love_languages: Record<string, number>;
  communication_style: string;
  conflict_resolution: string;
  attachment_style: string;
}
