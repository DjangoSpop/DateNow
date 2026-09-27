import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { isApiError } from '../../api/errors';
import { Brand } from '../../components/Brand';
import { Button, Card, ErrorBanner, Screen, TextField } from '../../components/ui';
import { useAuthStore } from '../../state/authStore';
import { spacing, type } from '../../theme';

export default function LoginScreen() {
  const login = useAuthStore((s) => s.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit() {
    const errs: typeof fieldErrors = {};
    if (!email.trim()) errs.email = 'Please enter your email.';
    if (!password) errs.password = 'Please enter your password.';
    setFieldErrors(errs);
    setError(null);
    if (Object.keys(errs).length) return;

    setSubmitting(true);
    try {
      await login(email, password);
      // Root layout re-routes based on /auth/me.
    } catch (e) {
      if (isApiError(e)) {
        if (e.code === 'unauthorized') setError(e.message || 'Incorrect email or password');
        else if (e.fieldErrors) setFieldErrors({ email: e.fieldErrors.email, password: e.fieldErrors.password });
        else setError(e.message);
      } else {
        setError('Something unexpected happened.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <Brand title="Welcome back" subtitle="Sign in to continue your journey" />
      <Card>
        {error ? <ErrorBanner message={error} /> : null}
        <TextField
          label="Email"
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          textContentType="emailAddress"
          placeholder="you@example.com"
          error={fieldErrors.email}
          returnKeyType="next"
        />
        <TextField
          label="Password"
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete="current-password"
          textContentType="password"
          placeholder="Your password"
          error={fieldErrors.password}
          returnKeyType="go"
          onSubmitEditing={() => void onSubmit()}
        />
        <Button label="Sign in" onPress={() => void onSubmit()} loading={submitting} />
      </Card>
      <View style={styles.footer}>
        <Text style={type.body}>New to DateNow?</Text>
        <Button
          label="Create an account"
          variant="ghost"
          onPress={() => router.push('/register')}
          accessibilityHint="Opens the registration form"
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  footer: { alignItems: 'center', marginTop: spacing.sm, gap: 0 },
});
