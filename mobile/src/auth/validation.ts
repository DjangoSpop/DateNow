/** Client-side mirror of the contract's credential rules (server stays authoritative). */
export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(email: string): string | undefined {
  const v = email.trim();
  if (!v) return 'Please enter your email.';
  if (!EMAIL_RE.test(v)) return 'That email address doesn’t look right.';
  return undefined;
}

export function validatePassword(password: string): string | undefined {
  if (!password) return 'Please enter a password.';
  if (password.length < PASSWORD_MIN) return `Use at least ${PASSWORD_MIN} characters.`;
  if (password.length > PASSWORD_MAX) return `Use at most ${PASSWORD_MAX} characters.`;
  return undefined;
}

export interface CredentialErrors {
  email?: string;
  password?: string;
  confirm?: string;
}

export function validateRegistration(
  email: string,
  password: string,
  confirm: string,
): CredentialErrors {
  const errors: CredentialErrors = {
    email: validateEmail(email),
    password: validatePassword(password),
    confirm: password !== confirm ? 'Passwords don’t match.' : undefined,
  };
  return stripEmpty(errors);
}

export function validateLogin(email: string, password: string): CredentialErrors {
  return stripEmpty({
    email: validateEmail(email),
    password: password ? undefined : 'Please enter your password.',
  });
}

function stripEmpty(e: CredentialErrors): CredentialErrors {
  const out: CredentialErrors = {};
  for (const [k, v] of Object.entries(e) as [keyof CredentialErrors, string | undefined][]) {
    if (v) out[k] = v;
  }
  return out;
}

/** Pick server `fields` for email/password (tolerating prefixed keys like `body.email`). */
export function mapCredentialFieldErrors(fields: Record<string, string> | undefined): CredentialErrors {
  const out: CredentialErrors = {};
  if (!fields) return out;
  for (const [key, msg] of Object.entries(fields)) {
    if (key.split('.').includes('email')) out.email ??= msg;
    else if (key.split('.').includes('password')) out.password ??= msg;
  }
  return out;
}
