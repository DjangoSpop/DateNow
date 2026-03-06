/**
 * Core types for the DateNow Next.js implementation
 */

export type Gender = 'male' | 'female' | 'non_binary' | 'other';

export type RelationshipGoal = 'serious' | 'casual' | 'friendship' | 'unsure';

export type MatchStatus = 'pending' | 'accepted' | 'rejected' | 'ai_mediation' | 'direct_chat' | 'ended';

export type SessionStage =
  | 'consent'
  | 'icebreakers'
  | 'values'
  | 'lifestyle'
  | 'reflection'
  | 'readiness'
  | 'outcome';

export interface UserProfile {
  id: string;
  firstName: string;
  lastName?: string;
  dateOfBirth: string;
  gender: Gender;
  bio: string;
  city: string;
  country: string;
  photos: string[];
  relationshipGoal: RelationshipGoal;
}

export interface PsychologicalProfile {
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
  familyOrientation: number;
  careerAmbition: number;
  adventureSeeking: number;
  socialConsciousness: number;
  spiritualReligious: number;
  communicationStyle: 'direct' | 'diplomatic' | 'emotional' | 'logical';
  conflictResolution: 'avoidant' | 'collaborative' | 'competitive';
  attachmentStyle: 'secure' | 'anxious' | 'avoidant' | 'fearful-avoidant';
}

export interface Match {
  id: string;
  user1: UserProfile;
  user2: UserProfile;
  overallCompatibility: number;
  status: MatchStatus;
}

export interface Message {
  id: string;
  type: 'moderator' | 'user';
  content: string;
  senderId?: string;
  senderName?: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface ModeratedSession {
  id: string;
  matchId: string;
  stage: SessionStage;
  messages: Message[];
  questionsAsked: number;
  user1Ready: boolean;
  user2Ready: boolean;
  readinessResult?: ReadinessResult;
}

export interface ReadinessResult {
  score: number;
  recommendation: 'continue_guided' | 'unlock_direct' | 'suggest_meeting' | 'slow_down' | 'mismatch';
  compatibilityDimensions: {
    values: number;
    communication: number;
    lifestyle: number;
    emotional: number;
  };
  moderatorNotes: string;
  confidence: number;
}
