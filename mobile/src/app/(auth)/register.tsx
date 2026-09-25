import { Link } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, Text, View, type TextInput } from 'react-native';

import { describeError, isApiError } from '@/api/errors';
import { useAuthStore } from '@/auth/authStore';
import {
  PASSWORD_MAX,
  PASSWORD_MIN,
  mapCredentialFieldErrors,
  validateRegistration,
  type CredentialErrors,
} from '@/auth/validation';
import { Button } from '@/components/Button';
import { Banner, Card } from '@/components/feedback';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { colors, spacing, touchTarget, typography } from '@/theme';

export default function RegisterScreen() {
  const register = useAuthStore((s) => s.register);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState<CredentialErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [emailTaken, setEmailTaken] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const passwordRef = useRef<TextInput>(null);
  const confirmRef = useRef<TextInput>(null);

  async function submit() {
    setFormError(null);
    setEmailTaken(false);
    const clientErrors = validateRegistration(email, password, confirm);
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length > 0) return;
    setSubmitting(true);
    try {
      await register(email, password);
    } catch (e) {
      if (isApiError(e) && e.code === 'EMAIL_TAKEN') {
        setEmailTaken(true);
        setErrors({ email: 'This email is already registered.' });
      } else {
        const fieldErrors = isApiError(e) ? mapCredentialFieldErrors(e.fields) : {};
        setErrors(fieldErrors);
        setFormError(describeError(e));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen centered>
      <View style={styles.header}>
        <Text style={styles.brand} accessibilityRole="header">
          Create your account
        </Text>
        <Text style={styles.subtitle}>It only takes a minute. Your details stay private.</Text>
      </View>

      {formError ? <Banner tone="error">{formError}</Banner> : null}
      {emailTaken ? (
        <Banner tone="info">
          You already have an account with this email. Sign in instead, or use a different email.
        </Banner>
      ) : null}

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
          hint={`${PASSWORD_MIN}–${PASSWORD_MAX} characters.`}
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
          maxLength={PASSWORD_MAX}
          returnKeyType="next"
          onSubmitEditing={() => confirmRef.current?.focus()}
        />
        <TextField
          ref={confirmRef}
          label="Confirm password"
          value={confirm}
          onChangeText={setConfirm}
          error={errors.confirm}
          secureTextEntry
          autoComplete="new-password"
          textContentType="newPassword"
          maxLength={PASSWORD_MAX}
          returnKeyType="go"
          onSubmitEditing={() => void submit()}
        />
        <Button label="Create account" onPress={() => void submit()} loading={submitting} />
        {emailTaken ? (
          <Link href="/login" replace style={styles.link} accessibilityRole="link">
            Go to sign in
          </Link>
        ) : null}
      </Card>

      <View style={styles.footer}>
        <Text style={typography.body}>Already have an account?</Text>
        <Link href="/login" replace style={styles.link} accessibilityRole="link">
          Sign in
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
    textAlign: 'center',
    paddingVertical: (touchTarget - 24) / 2,
  },
});
