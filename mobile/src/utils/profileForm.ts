import type { Gender, ProfileCreate, RelationshipGoal } from '../api/types';

export interface ProfileFormValues {
  first_name: string;
  last_name: string;
  date_of_birth: string; // YYYY-MM-DD as typed
  gender: Gender | null;
  looking_for_gender: Gender[];
  age_preference_min: string;
  age_preference_max: string;
  distance_preference_km: string;
  relationship_goal: RelationshipGoal | null;
  city: string;
  country: string;
  height_cm: string;
  bio: string;
}

export type ProfileFormErrors = Partial<Record<keyof ProfileFormValues, string>>;

export const GENDER_OPTIONS: { value: Gender; label: string }[] = [
  { value: 'female', label: 'Woman' },
  { value: 'male', label: 'Man' },
  { value: 'non_binary', label: 'Non-binary' },
  { value: 'other', label: 'Other' },
];

export const RELATIONSHIP_GOAL_OPTIONS: { value: RelationshipGoal; label: string }[] = [
  { value: 'serious', label: 'Something serious' },
  { value: 'casual', label: 'Something casual' },
  { value: 'friendship', label: 'Friendship first' },
  { value: 'unsure', label: 'Still figuring it out' },
];

export function emptyProfileForm(firstName = '', lastName = ''): ProfileFormValues {
  return {
    first_name: firstName,
    last_name: lastName,
    date_of_birth: '',
    gender: null,
    looking_for_gender: [],
    age_preference_min: '25',
    age_preference_max: '35',
    distance_preference_km: '50',
    relationship_goal: null,
    city: '',
    country: '',
    height_cm: '',
    bio: '',
  };
}

/** Parses a strict YYYY-MM-DD calendar date; returns null for malformed or impossible dates. */
export function parseIsoDate(value: string): { y: number; m: number; d: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
  if (!match) return null;
  const y = Number(match[1]);
  const m = Number(match[2]);
  const d = Number(match[3]);
  const dt = new Date(Date.UTC(y, m - 1, d));
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return null;
  return { y, m, d };
}

/** Age in whole years on `today` (local calendar date). */
export function ageOn(dob: { y: number; m: number; d: number }, today: Date): number {
  const ty = today.getFullYear();
  const tm = today.getMonth() + 1;
  const td = today.getDate();
  let age = ty - dob.y;
  if (tm < dob.m || (tm === dob.m && td < dob.d)) age -= 1;
  return age;
}

export function isAtLeast18(dateOfBirth: string, today: Date = new Date()): boolean {
  const dob = parseIsoDate(dateOfBirth);
  if (!dob) return false;
  return ageOn(dob, today) >= 18;
}

function parseIntStrict(v: string): number | null {
  if (!/^\d+$/.test(v.trim())) return null;
  return Number(v.trim());
}

/** Client-side checks for fast feedback. The server enforces the same rules authoritatively. */
export function validateProfileForm(values: ProfileFormValues, today: Date = new Date()): ProfileFormErrors {
  const errors: ProfileFormErrors = {};
  if (!values.first_name.trim()) errors.first_name = 'Please enter your first name.';

  const dob = parseIsoDate(values.date_of_birth);
  if (!dob) {
    errors.date_of_birth = 'Use the format YYYY-MM-DD.';
  } else if (ageOn(dob, today) < 18) {
    errors.date_of_birth = 'You must be at least 18 to use DateNow.';
  } else if (ageOn(dob, today) > 120) {
    errors.date_of_birth = 'Please check your date of birth.';
  }

  if (!values.gender) errors.gender = 'Please choose one.';
  if (!values.looking_for_gender.length) errors.looking_for_gender = 'Choose at least one.';

  const min = parseIntStrict(values.age_preference_min);
  const max = parseIntStrict(values.age_preference_max);
  if (min === null || min < 18 || min > 100) errors.age_preference_min = 'Between 18 and 100.';
  if (max === null || max < 18 || max > 100) errors.age_preference_max = 'Between 18 and 100.';
  if (min !== null && max !== null && !errors.age_preference_min && !errors.age_preference_max && min > max) {
    errors.age_preference_max = 'Must be at least the minimum age.';
  }

  const dist = parseIntStrict(values.distance_preference_km);
  if (dist === null || dist < 1) errors.distance_preference_km = 'Enter a distance in km.';

  if (!values.relationship_goal) errors.relationship_goal = 'Please choose one.';

  if (values.height_cm.trim()) {
    const h = parseIntStrict(values.height_cm);
    if (h === null || h < 100 || h > 250) errors.height_cm = 'Enter your height in cm (100–250).';
  }
  if (values.bio.length > 500) errors.bio = 'Please keep your bio under 500 characters.';
  return errors;
}

/** Builds the POST /users/me/profile body. Only contract fields; empty optionals are omitted. */
export function toProfileCreate(values: ProfileFormValues): ProfileCreate {
  const body: ProfileCreate = {
    first_name: values.first_name.trim(),
    date_of_birth: values.date_of_birth.trim(),
    gender: values.gender as Gender,
    looking_for_gender: values.looking_for_gender,
    age_preference_min: Number(values.age_preference_min),
    age_preference_max: Number(values.age_preference_max),
    distance_preference_km: Number(values.distance_preference_km),
    relationship_goal: values.relationship_goal as RelationshipGoal,
  };
  if (values.last_name.trim()) body.last_name = values.last_name.trim();
  if (values.city.trim()) body.city = values.city.trim();
  if (values.country.trim()) body.country = values.country.trim();
  if (values.bio.trim()) body.bio = values.bio.trim();
  if (values.height_cm.trim()) body.height_cm = Number(values.height_cm);
  return body;
}
