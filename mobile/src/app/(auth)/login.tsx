import { Link } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, Text, View, type TextInput } from 'react-native';

import { describeError, isApiError } from '@/api/errors';
import { useAuthStore } from '@/auth/authStore';
import { mapCredentialFieldErrors, validateLogin, type CredentialErrors } from '@/auth/validation';
import { Button } from '@/components/Button';
import { Banner, Card } from '@/components/feedback';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { colors, spacing, touchTarget, typography } from '@/theme';

export default function LoginScreen() {
  const login = useAuthStore((s) => s.login);
  const signOutReason = useAuthStore((s) => s.signOutReason);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<CredentialErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const passwordRef = useRef<TextInput>(null);

  async function submit() {
    setFormError(null);
    const clientErrors = validateLogin(email, password);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length > 0) return;
    setSubmitting(true);
    try {
      await login(email, password);
      // Navigation happens via the (auth) layout once status becomes signedIn.
    } catch (e) {
      const fieldErrors = isApiError(e) ? mapCredentialFieldErrors(e.fields) : {};
      setErrors(fieldErrors);
      setFormError(describeError(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen centered>
      <View style={styles.header}>
        <Text style={styles.brand} accessibilityRole="header">
          Welcome back
        </Text>
        <Text style={styles.subtitle}>Sign in to continue to DateNow.</Text>
      </View>

      {signOutReason && !formError ? <Banner tone="info">{signOutReason}</Banner> : null}
      {formError ? <Banner tone="error">{formError}</Banner> : null}

      <Card>
        <TextField
          label="Email"
          value={email}
          onChangeText={setEmail}
          error={errors.email}
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="email"
          keyboardType="email-address"
          textContentType="username"
          returnKeyType="next"
          onSubmitEditing={() => passwordRef.current?.focus()}
        />
        <TextField
          ref={passwordRef}
          label="Password"
          value={password}
          onChangeText={setPassword}
          error={errors.password}
          secureTextEntry
          autoComplete="current-password"
          textContentType="password"
          returnKeyType="go"
          onSubmitEditing={() => void submit()}
        />
        <Button label="Sign in" onPress={() => void submit()} loading={submitting} />
      </Card>

      <View style={styles.footer}>
        <Text style={typography.body}>New to DateNow?</Text>
        <Link href="/register" replace style={styles.link} accessibilityRole="link">
          Create an account
        </Link>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: spacing.sm, alignItems: 'center' },
  brand: { ...typography.title, color: colors.primary700, textAlign: 'center' },
  subtitle: { ...typography.body, color: colors.textMuted, textAlign: 'center' },
  footer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    alignItems: 'center',
    gap: spacing.sm,
  },
  link: {
    color: colors.primary600,
    fontSize: 16,
    fontWeight: '600',
    paddingVertical: (touchTarget - 24) / 2,
  },
});
