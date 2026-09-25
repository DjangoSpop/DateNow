import { useState, type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { describeError, isApiError } from '@/api/errors';
import { GENDERS, RELATIONSHIP_GOALS, type Gender, type ProfileCreate } from '@/api/types';
import { Button } from '@/components/Button';
import { Chip } from '@/components/Chip';
import { Banner, Card } from '@/components/feedback';
import { TextField } from '@/components/TextField';
import { colors, spacing, typography } from '@/theme';
import { GENDER_LABELS, GOAL_LABELS, LOOKING_FOR_LABELS } from './labels';
import {
  LIMITS,
  mapServerFieldErrors,
  validateProfile,
  type ProfileErrors,
  type ProfileFormValues,
} from './validation';

interface Props {
  initialValues: ProfileFormValues;
  submitLabel: string;
  /** Throws ApiError on failure; field errors are mapped onto the form. */
  onSubmit: (payload: ProfileCreate) => Promise<void>;
}

/** Shared by profile setup (POST) and profile edit (PATCH). */
export function ProfileForm({ initialValues, submitLabel, onSubmit }: Props) {
  const [values, setValues] = useState<ProfileFormValues>(initialValues);
  const [errors, setErrors] = useState<ProfileErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const set = <K extends keyof ProfileFormValues>(key: K, value: ProfileFormValues[K]) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  const toggleLookingFor = (g: Gender) =>
    set(
      'lookingFor',
      values.lookingFor.includes(g)
        ? values.lookingFor.filter((x) => x !== g)
        : [...values.lookingFor, g],
    );

  async function handleSubmit() {
    setFormError(null);
    const { errors: clientErrors, payload } = validateProfile(values);
    setErrors(clientErrors);
    if (!payload) {
      setFormError('A few details need another look.');
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit(payload);
    } catch (e) {
      const mapped = isApiError(e) ? mapServerFieldErrors(e.fields) : {};
      setErrors(mapped);
      setFormError(
        Object.keys(mapped).length > 0 ? 'A few details need another look.' : describeError(e),
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <View style={styles.form}>
      {formError ? <Banner tone="error">{formError}</Banner> : null}

      <Card>
        <Text style={typography.heading} accessibilityRole="header">
          About you
        </Text>
        <TextField
          label="First name"
          value={values.firstName}
          onChangeText={(t) => set('firstName', t)}
          error={errors.first_name}
          autoComplete="given-name"
          textContentType="givenName"
          maxLength={LIMITS.firstName}
        />
        <TextField
          label="Last name (optional)"
          value={values.lastName}
          onChangeText={(t) => set('lastName', t)}
          error={errors.last_name}
          autoComplete="family-name"
          textContentType="familyName"
          maxLength={LIMITS.lastName}
        />

        <FieldGroup label="Date of birth" error={errors.date_of_birth} hint="You must be 18 or older.">
          <View style={styles.row}>
            <TextField
              label="Day"
              placeholder="DD"
              value={values.dobDay}
              onChangeText={(t) => set('dobDay', t.replace(/\D/g, ''))}
              keyboardType="number-pad"
              maxLength={2}
              flex={1}
            />
            <TextField
              label="Month"
              placeholder="MM"
              value={values.dobMonth}
              onChangeText={(t) => set('dobMonth', t.replace(/\D/g, ''))}
              keyboardType="number-pad"
              maxLength={2}
              flex={1}
            />
            <TextField
              label="Year"
              placeholder="YYYY"
              value={values.dobYear}
              onChangeText={(t) => set('dobYear', t.replace(/\D/g, ''))}
              keyboardType="number-pad"
              maxLength={4}
              flex={1.4}
            />
          </View>
        </FieldGroup>

        <FieldGroup label="I am" error={errors.gender}>
          <View style={styles.chips} accessibilityRole="radiogroup">
            {GENDERS.map((g) => (
              <Chip
                key={g}
                label={GENDER_LABELS[g]}
                selected={values.gender === g}
                onPress={() => set('gender', g)}
              />
            ))}
          </View>
        </FieldGroup>
      </Card>

      <Card>
        <Text style={typography.heading} accessibilityRole="header">
          Who you&apos;d like to meet
        </Text>
        <FieldGroup
          label="Interested in"
          error={errors.looking_for_gender}
          hint="Choose all that apply."
        >
          <View style={styles.chips}>
            {GENDERS.map((g) => (
              <Chip
                key={g}
                role="checkbox"
                label={LOOKING_FOR_LABELS[g]}
                selected={values.lookingFor.includes(g)}
                onPress={() => toggleLookingFor(g)}
              />
            ))}
          </View>
        </FieldGroup>

        <FieldGroup label="Age range" hint="Between 18 and 100.">
          <View style={styles.row}>
            <TextField
              label="From"
              value={values.ageMin}
              onChangeText={(t) => set('ageMin', t.replace(/\D/g, ''))}
              keyboardType="number-pad"
              maxLength={3}
              error={errors.age_preference_min}
              flex={1}
            />
            <TextField
              label="To"
              value={values.ageMax}
              onChangeText={(t) => set('ageMax', t.replace(/\D/g, ''))}
              keyboardType="number-pad"
              maxLength={3}
              error={errors.age_preference_max}
              flex={1}
            />
          </View>
        </FieldGroup>

        <FieldGroup label="I'm looking for" error={errors.relationship_goal}>
          <View style={styles.chips} accessibilityRole="radiogroup">
            {RELATIONSHIP_GOALS.map((g) => (
              <Chip
                key={g}
                label={GOAL_LABELS[g]}
                selected={values.goal === g}
                onPress={() => set('goal', g)}
              />
            ))}
          </View>
        </FieldGroup>
      </Card>

      <Card>
        <Text style={typography.heading} accessibilityRole="header">
          A little more (optional)
        </Text>
        <TextField
          label="Bio"
          value={values.bio}
          onChangeText={(t) => set('bio', t)}
          error={errors.bio}
          hint={`${values.bio.length}/${LIMITS.bio}`}
          multiline
          maxLength={LIMITS.bio}
          numberOfLines={4}
          textAlignVertical="top"
        />
        <TextField
          label="City"
          value={values.city}
          onChangeText={(t) => set('city', t)}
          error={errors.city}
          maxLength={LIMITS.place}
          autoComplete="address-line2"
        />
        <TextField
          label="Country"
          value={values.country}
          onChangeText={(t) => set('country', t)}
          error={errors.country}
          maxLength={LIMITS.place}
          autoComplete="country"
        />
      </Card>

      <Button label={submitLabel} onPress={handleSubmit} loading={submitting} />
    </View>
  );
}

function FieldGroup({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <View style={styles.group} accessible={false}>
      <Text style={typography.label}>{label}</Text>
      {hint ? <Text style={typography.small}>{hint}</Text> : null}
      {children}
      {error ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {error}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  form: { gap: spacing.lg },
  group: { gap: spacing.sm },
  row: { flexDirection: 'row', gap: spacing.md, alignItems: 'flex-start' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  error: { fontSize: 14, color: colors.danger700 },
});
