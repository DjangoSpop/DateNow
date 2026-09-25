import { router } from 'expo-router';
import { useEffect, useState } from 'react';

import * as endpoints from '@/api/endpoints';
import { describeError } from '@/api/errors';
import type { Profile, ProfileCreate } from '@/api/types';
import { ErrorState, LoadingState } from '@/components/feedback';
import { Screen } from '@/components/Screen';
import { ProfileForm } from '@/features/profile/ProfileForm';
import { diffForUpdate, profileToForm } from '@/features/profile/validation';

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; profile: Profile };

function leave() {
  if (router.canGoBack()) router.back();
  else router.replace('/home');
}

export default function ProfileEditScreen() {
  const [state, setState] = useState<LoadState>({ kind: 'loading' });

  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    endpoints.getProfile().then(
      (profile) => active && setState({ kind: 'ready', profile }),
      (e: unknown) => active && setState({ kind: 'error', message: describeError(e) }),
    );
    return () => {
      active = false;
    };
  }, [attempt]);

  const retry = () => {
    setState({ kind: 'loading' });
    setAttempt((n) => n + 1);
  };

  async function save(payload: ProfileCreate) {
    if (state.kind !== 'ready') return;
    const update = diffForUpdate(state.profile, payload);
    if (Object.keys(update).length > 0) {
      await endpoints.updateProfile(update);
    }
    leave();
  }

  if (state.kind === 'loading') return <LoadingState label="Loading your profile…" />;
  if (state.kind === 'error') return <ErrorState message={state.message} onRetry={retry} />;

  return (
    <Screen>
      <ProfileForm
        initialValues={profileToForm(state.profile)}
        submitLabel="Save changes"
        onSubmit={save}
      />
    </Screen>
  );
}
