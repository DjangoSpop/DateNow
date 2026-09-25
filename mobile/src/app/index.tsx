import { Redirect } from 'expo-router';

import { useAuthStore } from '@/auth/authStore';
import { homeFor } from '@/auth/routing';

/** Entry route: send the user wherever their auth + onboarding state says they belong. */
export default function Index() {
  const status = useAuthStore((s) => s.status);
  const me = useAuthStore((s) => s.me);
  if (status !== 'signedIn' || !me) return <Redirect href="/login" />;
  return <Redirect href={homeFor(me.onboarding)} />;
}
