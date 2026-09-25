import type { Gender, Profile, ProfileCreate, ProfileUpdate, RelationshipGoal } from '@/api/types';

/** Form state: text inputs are strings; keys of errors are the API field names. */
export interface ProfileFormValues {
  firstName: string;
  lastName: string;
  dobDay: string;
  dobMonth: string;
  dobYear: string;
  gender: Gender | null;
  lookingFor: Gender[];
  ageMin: string;
  ageMax: string;
  goal: RelationshipGoal | null;
  bio: string;
  city: string;
  country: string;
}

export type ProfileField = keyof ProfileCreate;
export type ProfileErrors = Partial<Record<ProfileField, string>>;

export const LIMITS = {
  firstName: 50,
  lastName: 50,
  bio: 500,
  place: 100,
  minAge: 18,
  maxAge: 120,
  prefMin: 18,
  prefMax: 100,
} as const;

export const emptyProfileForm: ProfileFormValues = {
  firstName: '',
  lastName: '',
  dobDay: '',
  dobMonth: '',
  dobYear: '',
  gender: null,
  lookingFor: [],
  ageMin: '25',
  ageMax: '40',
  goal: null,
  bio: '',
  city: '',
  country: '',
};

export function profileToForm(p: Profile): ProfileFormValues {
  const [y = '', m = '', d = ''] = p.date_of_birth.split('-');
  return {
    firstName: p.first_name,
    lastName: p.last_name ?? '',
    dobDay: d,
    dobMonth: m,
    dobYear: y,
    gender: p.gender,
    lookingFor: [...p.looking_for_gender],
    ageMin: String(p.age_preference_min),
    ageMax: String(p.age_preference_max),
    goal: p.relationship_goal,
    bio: p.bio ?? '',
    city: p.city ?? '',
    country: p.country ?? '',
  };
}

const pad2 = (n: number) => String(n).padStart(2, '0');

/** Returns an ISO date string if the parts form a real calendar date, else null. */
export function toIsoDate(day: string, month: string, year: string): string | null {
  if (!/^\d{1,2}$/.test(day) || !/^\d{1,2}$/.test(month) || !/^\d{4}$/.test(year)) return null;
  const d = Number(day);
  const m = Number(month);
  const y = Number(year);
  const date = new Date(Date.UTC(y, m - 1, d));
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== m - 1 || date.getUTCDate() !== d) {
    return null;
  }
  return `${y}-${pad2(m)}-${pad2(d)}`;
}

/** Whole years between an ISO birth date and `today` (local calendar date). */
export function ageOn(isoDob: string, today: Date): number {
  const [y, m, d] = isoDob.split('-').map(Number) as [number, number, number];
  let age = today.getFullYear() - y;
  const beforeBirthday =
    today.getMonth() + 1 < m || (today.getMonth() + 1 === m && today.getDate() < d);
  if (beforeBirthday) age -= 1;
  return age;
}

function isFuture(isoDob: string, today: Date): boolean {
  const todayIso = `${today.getFullYear()}-${pad2(today.getMonth() + 1)}-${pad2(today.getDate())}`;
  return isoDob > todayIso;
}

function parseIntStrict(v: string): number | null {
  return /^\d{1,3}$/.test(v.trim()) ? Number(v.trim()) : null;
}

const optional = (v: string): string | null => (v.trim() === '' ? null : v.trim());

/**
 * Client-side mirror of the contract's ProfileCreate rules. The server remains the authority;
 * this only gives faster, friendlier feedback.
 */
export function validateProfile(
  v: ProfileFormValues,
  today: Date = new Date(),
): { errors: ProfileErrors; payload: ProfileCreate | null } {
  const errors: ProfileErrors = {};

  const firstName = v.firstName.trim();
  if (!firstName) errors.first_name = 'Please add your first name.';
  else if (firstName.length > LIMITS.firstName)
    errors.first_name = `Keep it under ${LIMITS.firstName} characters.`;

  if (v.lastName.trim().length > LIMITS.lastName)
    errors.last_name = `Keep it under ${LIMITS.lastName} characters.`;

  const dob = toIsoDate(v.dobDay.trim(), v.dobMonth.trim(), v.dobYear.trim());
  if (!dob) errors.date_of_birth = 'Please enter a valid date (day, month, 4-digit year).';
  else if (isFuture(dob, today)) errors.date_of_birth = "That date hasn't happened yet.";
  else {
    const age = ageOn(dob, today);
    if (age < LIMITS.minAge) errors.date_of_birth = 'You need to be 18 or older to use DateNow.';
    else if (age > LIMITS.maxAge) errors.date_of_birth = 'Please check the year.';
  }

  if (!v.gender) errors.gender = 'Please choose the option that fits you best.';

  const lookingFor = Array.from(new Set(v.lookingFor));
  if (lookingFor.length === 0) errors.looking_for_gender = 'Choose at least one.';

  const min = parseIntStrict(v.ageMin);
  const max = parseIntStrict(v.ageMax);
  if (min === null || min < LIMITS.prefMin || min > LIMITS.prefMax)
    errors.age_preference_min = `Enter an age from ${LIMITS.prefMin} to ${LIMITS.prefMax}.`;
  if (max === null || max < LIMITS.prefMin || max > LIMITS.prefMax)
    errors.age_preference_max = `Enter an age from ${LIMITS.prefMin} to ${LIMITS.prefMax}.`;
  if (min !== null && max !== null && !errors.age_preference_min && !errors.age_preference_max) {
    if (min > max) errors.age_preference_max = 'The maximum must be at least the minimum.';
  }

  if (!v.goal) errors.relationship_goal = 'Please choose what you are looking for.';

  if (v.bio.trim().length > LIMITS.bio) errors.bio = `Keep it under ${LIMITS.bio} characters.`;
  if (v.city.trim().length > LIMITS.place) errors.city = `Keep it under ${LIMITS.place} characters.`;
  if (v.country.trim().length > LIMITS.place)
    errors.country = `Keep it under ${LIMITS.place} characters.`;

  if (Object.keys(errors).length > 0) return { errors, payload: null };

  const payload: ProfileCreate = {
    first_name: firstName,
    last_name: optional(v.lastName),
    date_of_birth: dob!,
    gender: v.gender!,
    looking_for_gender: lookingFor,
    age_preference_min: min!,
    age_preference_max: max!,
    relationship_goal: v.goal!,
    bio: optional(v.bio),
    city: optional(v.city),
    country: optional(v.country),
  };
  return { errors, payload };
}

/** Body for POST: optional fields that are empty are omitted rather than sent as null. */
export function toCreateBody(p: ProfileCreate): ProfileCreate {
  const body: ProfileCreate = { ...p };
  for (const k of ['last_name', 'bio', 'city', 'country'] as const) {
    if (body[k] === null) delete body[k];
  }
  return body;
}

/** Body for PATCH: only fields whose value differs from the current profile. */
export function diffForUpdate(current: Profile, next: ProfileCreate): ProfileUpdate {
  const update: Record<string, unknown> = {};
  for (const key of Object.keys(next) as ProfileField[]) {
    const a = next[key];
    const b = current[key];
    const same =
      Array.isArray(a) && Array.isArray(b)
        ? a.length === b.length && [...a].sort().join() === [...b].sort().join()
        : (a ?? null) === (b ?? null);
    if (!same) update[key] = a ?? null;
  }
  return update as ProfileUpdate;
}

/**
 * Map server `fields` onto form fields. Tolerates prefixed/nested keys such as
 * `body.first_name` or `looking_for_gender.0` in case the server reports locations that way.
 */
export function mapServerFieldErrors(fields: Record<string, string> | undefined): ProfileErrors {
  const out: ProfileErrors = {};
  if (!fields) return out;
  const known: ProfileField[] = [
    'first_name',
    'last_name',
    'date_of_birth',
    'gender',
    'looking_for_gender',
    'age_preference_min',
    'age_preference_max',
    'relationship_goal',
    'bio',
    'city',
    'country',
  ];
  for (const [rawKey, message] of Object.entries(fields)) {
    const key = rawKey.split('.').find((part) => (known as string[]).includes(part));
    if (key && !out[key as ProfileField]) out[key as ProfileField] = message;
  }
  return out;
}
