/**
 * Types mirroring docs/API_CONTRACT.md (Sprint 1 draft). Keep in sync with the contract;
 * do not add fields the contract does not define.
 */

// ---------- Tokens / Auth ----------

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export type OnboardingStatus = 'not_started' | 'in_progress' | 'completed';

export interface Me {
  id: number;
  email: string;
  first_name: string;
  last_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  has_profile: boolean;
  onboarding_status: OnboardingStatus;
}

// ---------- Profile ----------

export type Gender = 'male' | 'female' | 'non_binary' | 'other';
export type RelationshipGoal = 'serious' | 'casual' | 'friendship' | 'unsure';

export interface ProfileCreate {
  first_name: string;
  last_name?: string;
  /** ISO date, YYYY-MM-DD */
  date_of_birth: string;
  gender: Gender;
  bio?: string;
  city?: string;
  country?: string;
  height_cm?: number;
  looking_for_gender: Gender[];
  age_preference_min: number;
  age_preference_max: number;
  distance_preference_km: number;
  relationship_goal: RelationshipGoal;
}

export type ProfileUpdate = Partial<ProfileCreate>;

export interface Profile {
  id: number;
  user_id: number;
  first_name: string;
  last_name: string | null;
  date_of_birth: string;
  gender: Gender;
  bio: string | null;
  city: string | null;
  country: string | null;
  height_cm: number | null;
  looking_for_gender: Gender[];
  age_preference_min: number;
  age_preference_max: number;
  distance_preference_km: number;
  relationship_goal: RelationshipGoal;
  is_profile_complete: boolean;
  photos: unknown[] | null;
  profile_photo_url: string | null;
  created_at: string;
  updated_at: string | null;
}

// ---------- Questionnaire / Onboarding ----------

export type QuestionType = 'scale' | 'single_choice' | 'multiple_choice' | 'text';

export interface QuestionScale {
  min: number;
  max: number;
  min_label: string;
  max_label: string;
}

export interface Question {
  id: string;
  text: string;
  type: QuestionType;
  required: boolean;
  options: string[] | null;
  scale: QuestionScale | null;
  max_length: number | null;
}

export interface QuestionnaireSection {
  id: string;
  title: string;
  description: string;
  questions: Question[];
}

export interface QuestionnaireDefinition {
  version: string;
  sections: QuestionnaireSection[];
}

/** A raw answer value: scale → number, single_choice/text → string, multiple_choice → string[]. */
export type AnswerValue = number | string | string[];
export type Answers = Record<string, AnswerValue>;

export interface OnboardingState {
  status: OnboardingStatus;
  current_section: string | null;
  answers: Answers;
  questionnaire_version: string;
  updated_at: string | null;
  completed_at: string | null;
}

export interface OnboardingDraftRequest {
  current_section: string | null;
  answers: Answers;
}

export interface QuestionnaireSubmitRequest {
  answers: Answers;
}

export interface PsychologicalProfile {
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
  family_orientation: number;
  career_ambition: number;
  adventure_seeking: number;
  social_consciousness: number;
  spiritual_religious: number;
  communication_style: string;
  conflict_resolution: string;
  love_language_words: number;
  love_language_acts: number;
  love_language_gifts: number;
  love_language_time: number;
  love_language_touch: number;
  attachment_style: string;
  questionnaire_version: string;
  created_at: string;
  updated_at: string | null;
}

// ---------- Health ----------

export interface HealthResponse {
  status: string;
  [key: string]: unknown;
}

// ---------- Errors ----------

export interface FastApiValidationItem {
  loc: (string | number)[];
  msg: string;
  type?: string;
}

/**
 * 422 item shape used by PUT /onboarding and POST /questionnaire/submit
 * (orchestrator clarification; `question_id: "__all__"` = whole-body error).
 */
export interface QuestionnaireValidationItem {
  question_id: string;
  message: string;
}

export interface FastApiErrorBody {
  detail?: string | (FastApiValidationItem | QuestionnaireValidationItem)[];
}
