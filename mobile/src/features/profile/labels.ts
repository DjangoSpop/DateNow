import type { Gender, RelationshipGoal } from '@/api/types';

/** How a person describes themselves. */
export const GENDER_LABELS: Record<Gender, string> = {
  male: 'Man',
  female: 'Woman',
  non_binary: 'Non-binary',
  other: 'Another identity',
};

/** Who someone would like to meet (plural phrasing). */
export const LOOKING_FOR_LABELS: Record<Gender, string> = {
  male: 'Men',
  female: 'Women',
  non_binary: 'Non-binary people',
  other: 'People of another identity',
};

export const GOAL_LABELS: Record<RelationshipGoal, string> = {
  serious: 'A long-term relationship',
  casual: 'Something casual',
  friendship: 'Friendship first',
  unsure: 'Still figuring it out',
};
