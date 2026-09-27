import {
  emptyProfileForm,
  isAtLeast18,
  parseIsoDate,
  toProfileCreate,
  validateProfileForm,
} from '../src/utils/profileForm';

const today = new Date(2026, 8, 27); // 2026-09-27 local

describe('profile form', () => {
  it('parses strict ISO dates only', () => {
    expect(parseIsoDate('1995-04-12')).toEqual({ y: 1995, m: 4, d: 12 });
    expect(parseIsoDate('1995-02-30')).toBeNull();
    expect(parseIsoDate('12/04/1995')).toBeNull();
  });

  it('enforces 18+ on the exact birthday boundary', () => {
    expect(isAtLeast18('2008-09-27', today)).toBe(true);
    expect(isAtLeast18('2008-09-28', today)).toBe(false);
    expect(isAtLeast18('garbage', today)).toBe(false);
  });

  it('validates required fields and min <= max', () => {
    const errors = validateProfileForm(
      { ...emptyProfileForm('Ada'), age_preference_min: '40', age_preference_max: '30' },
      today,
    );
    expect(errors.date_of_birth).toBeDefined();
    expect(errors.gender).toBeDefined();
    expect(errors.looking_for_gender).toBeDefined();
    expect(errors.relationship_goal).toBeDefined();
    expect(errors.age_preference_max).toMatch(/minimum/);
    expect(errors.first_name).toBeUndefined();
  });

  it('builds a contract-only body and omits empty optionals', () => {
    const body = toProfileCreate({
      ...emptyProfileForm('Ada', ''),
      date_of_birth: '1995-04-12',
      gender: 'female',
      looking_for_gender: ['male'],
      relationship_goal: 'serious',
      city: ' Paris ',
    });
    expect(body).toEqual({
      first_name: 'Ada',
      date_of_birth: '1995-04-12',
      gender: 'female',
      looking_for_gender: ['male'],
      age_preference_min: 25,
      age_preference_max: 35,
      distance_preference_km: 50,
      relationship_goal: 'serious',
      city: 'Paris',
    });
  });
});
