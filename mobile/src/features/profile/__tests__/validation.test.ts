import type { Profile } from '@/api/types';
import {
  ageOn,
  diffForUpdate,
  emptyProfileForm,
  mapServerFieldErrors,
  toCreateBody,
  toIsoDate,
  validateProfile,
  type ProfileFormValues,
} from '../validation';

const today = new Date(2026, 8, 25); // 25 Sep 2026 (local)

const valid: ProfileFormValues = {
  ...emptyProfileForm,
  firstName: ' Sam ',
  dobDay: '2',
  dobMonth: '4',
  dobYear: '1995',
  gender: 'female',
  lookingFor: ['male', 'non_binary'],
  ageMin: '27',
  ageMax: '38',
  goal: 'serious',
  city: 'Cairo',
};

describe('profile validation', () => {
  it('builds a contract-shaped payload', () => {
    const { errors, payload } = validateProfile(valid, today);
    expect(errors).toEqual({});
    expect(payload).toEqual({
      first_name: 'Sam',
      last_name: null,
      date_of_birth: '1995-04-02',
      gender: 'female',
      looking_for_gender: ['male', 'non_binary'],
      age_preference_min: 27,
      age_preference_max: 38,
      relationship_goal: 'serious',
      bio: null,
      city: 'Cairo',
      country: null,
    });
    expect(toCreateBody(payload!)).not.toHaveProperty('bio');
  });

  it('enforces 18+ exactly on the birthday boundary', () => {
    const turns18Today = { ...valid, dobDay: '25', dobMonth: '9', dobYear: '2008' };
    const turns18Tomorrow = { ...valid, dobDay: '26', dobMonth: '9', dobYear: '2008' };
    expect(validateProfile(turns18Today, today).errors.date_of_birth).toBeUndefined();
    expect(validateProfile(turns18Tomorrow, today).errors.date_of_birth).toMatch(/18/);
  });

  it('rejects impossible and future dates', () => {
    expect(toIsoDate('30', '2', '2000')).toBeNull();
    expect(toIsoDate('29', '2', '2000')).toBe('2000-02-29');
    expect(validateProfile({ ...valid, dobYear: '2027' }, today).errors.date_of_birth).toBeDefined();
    expect(ageOn('2000-09-26', today)).toBe(25);
  });

  it('checks looking-for and the age range', () => {
    const { errors } = validateProfile(
      { ...valid, lookingFor: [], ageMin: '40', ageMax: '30', gender: null, goal: null },
      today,
    );
    expect(errors.looking_for_gender).toBeDefined();
    expect(errors.age_preference_max).toMatch(/at least the minimum/);
    expect(errors.gender).toBeDefined();
    expect(errors.relationship_goal).toBeDefined();
    expect(validateProfile({ ...valid, ageMin: '17' }, today).errors.age_preference_min).toBeDefined();
    expect(validateProfile({ ...valid, ageMax: '101' }, today).errors.age_preference_max).toBeDefined();
  });

  it('maps server field errors, tolerating prefixed keys', () => {
    expect(
      mapServerFieldErrors({ date_of_birth: 'must be 18+', 'body.looking_for_gender.0': 'bad' }),
    ).toEqual({ date_of_birth: 'must be 18+', looking_for_gender: 'bad' });
  });

  it('PATCH body contains only changed fields', () => {
    const current: Profile = {
      first_name: 'Sam',
      last_name: null,
      date_of_birth: '1995-04-02',
      age: 31,
      gender: 'female',
      looking_for_gender: ['non_binary', 'male'],
      age_preference_min: 27,
      age_preference_max: 38,
      relationship_goal: 'serious',
      bio: 'hi',
      city: 'Cairo',
      country: null,
      created_at: '',
      updated_at: '',
    };
    const { payload } = validateProfile({ ...valid, ageMax: '40', bio: '' }, today);
    expect(diffForUpdate(current, payload!)).toEqual({ age_preference_max: 40, bio: null });
  });
});
