import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { isApiError } from '../../api/errors';
import { Brand } from '../../components/Brand';
import { Button, Card, ErrorBanner, Screen, TextField } from '../../components/ui';
import { useAuthStore } from '../../state/authStore';
import { spacing, type } from '../../theme';

type Field = 'first_name' | 'last_name' | 'email' | 'password' | 'confirm';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function RegisterScreen() {
  const register = useAuthStore((s) => s.register);
  const [values, setValues] = useState<Record<Field, string>>({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm: '',
  });
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const set = (field: Field) => (text: string) => setValues((v) => ({ ...v, [field]: text }));

  function validate(): Partial<Record<Field, string>> {
    const e: Partial<Record<Field, string>> = {};
    if (!values.first_name.trim()) e.first_name = 'Please enter your first name.';
    if (!EMAIL_RE.test(values.email.trim())) e.email = 'Please enter a valid email.';
    if (values.password.length < 8) e.password = 'Use at least 8 characters.';
    if (values.confirm !== values.password) e.confirm = "Passwords don't match.";
    return e;
  }

  async function onSubmit() {
    const e = validate();
    setErrors(e);
    setError(null);
    if (Object.keys(e).length) return;

    setSubmitting(true);
    try {
      await register({
        email: values.email.trim(),
        password: values.password,
        first_name: values.first_name.trim(),
        ...(values.last_name.trim() ? { last_name: values.last_name.trim() } : {}),
      });
    } catch (err) {
      if (isApiError(err)) {
        if (err.code === 'conflict') {
          setErrors({ email: 'An account with this email already exists.' });
        } else if (err.fieldErrors) {
          setErrors(err.fieldErrors as Partial<Record<Field, string>>);
          if (!Object.keys(err.fieldErrors).some((k) => k in values)) setError(err.message);
        } else {
          setError(err.message);
        }
      } else {
        setError('Something unexpected happened.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <Brand title="Create your account" subtitle="Meaningful connections start here" />
      <Card>
        {error ? <ErrorBanner message={error} /> : null}
        <TextField
          label="First name"
          value={values.first_name}
          onChangeText={set('first_name')}
          autoComplete="given-name"
          textContentType="givenName"
          error={errors.first_name}
        />
        <TextField
          label="Last name (optional)"
          value={values.last_name}
          onChangeText={set('last_name')}
          autoComplete="family-name"
          textContentType="familyName"
          error={errors.last_name}
        />
        <TextField
          label="Email"
          value={values.email}
          onChangeText={set('email')}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          textContentType="emailAddress"
          error={errors.email}
        />
        <TextField
          label="Password"
          value={values.password}
          onChangeText={set('password')}
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
          hint="At least 8 characters"
          error={errors.password}
        />
        <TextField
          label="Confirm password"
          value={values.confirm}
          onChangeText={set('confirm')}
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
          error={errors.confirm}
          onSubmitEditing={() => void onSubmit()}
        />
        <Button label="Create account" onPress={() => void onSubmit()} loading={submitting} />
      </Card>
      <View style={styles.footer}>
        <Text style={type.body}>Already have an account?</Text>
        <Button
          label="Sign in"
          variant="ghost"
          onPress={() => (router.canGoBack() ? router.back() : router.replace('/login'))}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  footer: { alignItems: 'center', marginTop: spacing.sm },
});
