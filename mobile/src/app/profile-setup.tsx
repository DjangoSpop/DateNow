import { useState } from 'react';
import { Text } from 'react-native';

import { isApiError } from '../api/errors';
import { profile } from '../api/profile';
import type { Gender } from '../api/types';
import { Button, Card, Chip, ErrorBanner, FieldGroup, Screen, TextField } from '../components/ui';
import { useAuthStore } from '../state/authStore';
import { type } from '../theme';
import {
  GENDER_OPTIONS,
  RELATIONSHIP_GOAL_OPTIONS,
  emptyProfileForm,
  toProfileCreate,
  validateProfileForm,
  type ProfileFormErrors,
  type ProfileFormValues,
} from '../utils/profileForm';

export default function ProfileSetupScreen() {
  const me = useAuthStore((s) => s.me);
  const refreshMe = useAuthStore((s) => s.refreshMe);
  const logout = useAuthStore((s) => s.logout);

  const [values, setValues] = useState<ProfileFormValues>(() =>
    emptyProfileForm(me?.first_name ?? '', me?.last_name ?? ''),
  );
  const [errors, setErrors] = useState<ProfileFormErrors>({});
  const [error, setError] = useState<{ message: string; retryable: boolean } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function update<K extends keyof ProfileFormValues>(key: K, value: ProfileFormValues[K]) {
    setValues((v) => ({ ...v, [key]: value }));
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function toggleLookingFor(g: Gender) {
    update(
      'looking_for_gender',
      values.looking_for_gender.includes(g)
        ? values.looking_for_gender.filter((x) => x !== g)
        : [...values.looking_for_gender, g],
    );
  }

  async function onSubmit() {
    const clientErrors = validateProfileForm(values);
    setErrors(clientErrors);
    setError(null);
    if (Object.keys(clientErrors).length) {
      setError({ message: 'Please fix the highlighted fields.', retryable: false });
      return;
    }
    setSubmitting(true);
    try {
      await profile.create(toProfileCreate(values));
      await refreshMe(); // has_profile → true; root layout moves on to onboarding.
    } catch (e) {
      if (!isApiError(e)) {
        setError({ message: 'Something unexpected happened.', retryable: true });
      } else if (e.status === 400) {
        // Profile already exists (e.g. created on another device): just move on.
        try {
          await refreshMe();
        } catch {
          setError({ message: e.message, retryable: true });
        }
      } else if (e.code === 'validation') {
        const serverErrors: ProfileFormErrors = {};
        for (const [field, msg] of Object.entries(e.fieldErrors ?? {})) {
          if (field in values) serverErrors[field as keyof ProfileFormValues] = msg;
        }
        setErrors(serverErrors);
        const unmapped = Object.keys(serverErrors).length === 0;
        setError({ message: unmapped ? e.message : 'Please fix the highlighted fields.', retryable: false });
      } else {
        setError({
          message: e.message,
          retryable: e.code === 'network' || e.code === 'timeout' || e.code === 'server',
        });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <Text style={type.title} accessibilityRole="header">
        About you
      </Text>
      <Text style={type.body}>A few basics so we can introduce you to the right people.</Text>

      <Card>
        <TextField
          label="First name"
          value={values.first_name}
          onChangeText={(t) => update('first_name', t)}
          error={errors.first_name}
        />
        <TextField
          label="Last name (optional)"
          value={values.last_name}
          onChangeText={(t) => update('last_name', t)}
          error={errors.last_name}
        />
        <TextField
          label="Date of birth"
          value={values.date_of_birth}
          onChangeText={(t) => update('date_of_birth', t)}
          placeholder="YYYY-MM-DD"
          keyboardType="numbers-and-punctuation"
          autoComplete="birthdate-full"
          maxLength={10}
          hint="You must be 18 or older."
          error={errors.date_of_birth}
        />
        <FieldGroup label="I am" error={errors.gender}>
          {GENDER_OPTIONS.map((o) => (
            <Chip key={o.value} label={o.label} selected={values.gender === o.value} onPress={() => update('gender', o.value)} />
          ))}
        </FieldGroup>
      </Card>

      <Card>
        <FieldGroup label="Interested in (choose all that apply)" error={errors.looking_for_gender}>
          {GENDER_OPTIONS.map((o) => (
            <Chip
              key={o.value}
              multi
              label={o.label}
              selected={values.looking_for_gender.includes(o.value)}
              onPress={() => toggleLookingFor(o.value)}
            />
          ))}
        </FieldGroup>
        <TextField
          label="Minimum age"
          value={values.age_preference_min}
          onChangeText={(t) => update('age_preference_min', t.replace(/\D/g, ''))}
          keyboardType="number-pad"
          maxLength={3}
          error={errors.age_preference_min}
        />
        <TextField
          label="Maximum age"
          value={values.age_preference_max}
          onChangeText={(t) => update('age_preference_max', t.replace(/\D/g, ''))}
          keyboardType="number-pad"
          maxLength={3}
          error={errors.age_preference_max}
        />
        <TextField
          label="Maximum distance (km)"
          value={values.distance_preference_km}
          onChangeText={(t) => update('distance_preference_km', t.replace(/\D/g, ''))}
          keyboardType="number-pad"
          maxLength={5}
          error={errors.distance_preference_km}
        />
        <FieldGroup label="Looking for" error={errors.relationship_goal}>
          {RELATIONSHIP_GOAL_OPTIONS.map((o) => (
            <Chip
              key={o.value}
              label={o.label}
              selected={values.relationship_goal === o.value}
              onPress={() => update('relationship_goal', o.value)}
            />
          ))}
        </FieldGroup>
      </Card>

      <Card>
        <TextField
          label="City (optional)"
          value={values.city}
          onChangeText={(t) => update('city', t)}
          autoComplete="postal-address-locality"
          error={errors.city}
        />
        <TextField
          label="Country (optional)"
          value={values.country}
          onChangeText={(t) => update('country', t)}
          autoComplete="country"
          error={errors.country}
        />
        <TextField
          label="Height in cm (optional)"
          value={values.height_cm}
          onChangeText={(t) => update('height_cm', t.replace(/\D/g, ''))}
          keyboardType="number-pad"
          maxLength={3}
          error={errors.height_cm}
        />
        <TextField
          label="Bio (optional)"
          value={values.bio}
          onChangeText={(t) => update('bio', t)}
          multiline
          maxLength={1000}
          placeholder="What should someone know about you?"
          error={errors.bio}
        />
      </Card>

      {error ? (
        <ErrorBanner message={error.message} onRetry={error.retryable ? () => void onSubmit() : undefined} />
      ) : null}
      <Button label="Continue" onPress={() => void onSubmit()} loading={submitting} />
      <Button label="Sign out" variant="ghost" onPress={() => void logout()} />
    </Screen>
  );
}
