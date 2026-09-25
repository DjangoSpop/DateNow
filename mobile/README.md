# DateNow Mobile

React Native + Expo (SDK 57) + TypeScript client for the Sprint 1 API in
[`docs/API_CONTRACT.md`](../docs/API_CONTRACT.md). It covers auth, profile setup and editing, the
questionnaire, and a home screen with a personality snapshot.

## Quick start

```bash
cd mobile
npm install
npm start            # Expo dev server; press i / a for a simulator, or scan the QR code
```

The app needs the backend running (default `http://localhost:8000`).

## Configuration

Config is resolved at build time in `app.config.ts` and read at runtime by `src/config.ts`.
There are two profiles, selected with `APP_ENV`:

| APP_ENV | API base URL | Notes |
|---|---|---|
| `development` (default) | `EXPO_PUBLIC_API_URL` if set, else `http://localhost:8000` (iOS simulator / web) or `http://10.0.2.2:8000` (Android emulator: this is how it reaches the host machine) | Plain http is fine for local dev |
| `production` | `EXPO_PUBLIC_API_URL` **required**, must be `https://` | The config fails the build if it is missing or not https |

The client appends `/api/v1` itself, so set only the origin:

```bash
# Physical device on the same Wi-Fi: use your computer's LAN IP
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000 npm start

# Production bundle
APP_ENV=production EXPO_PUBLIC_API_URL=https://api.example.com npx expo export
```

Keep secrets out of the app. Everything in `extra` and every `EXPO_PUBLIC_*` variable ends up
inside the shipped bundle.

## Architecture

```
src/
  app/                      expo-router routes (file-based)
    _layout.tsx             root: bootstrap session, boot screen while status = booting
    index.tsx               redirect by auth + onboarding state
    (auth)/_layout.tsx      guard: only while signed out
    (auth)/login.tsx, register.tsx
    (app)/_layout.tsx       guard: signed in + onboarding-aware redirects (deep links too)
    (app)/profile-setup.tsx, profile-edit.tsx, questionnaire.tsx, home.tsx
  api/
    client.ts               fetch wrapper: timeout, JSON, bearer, ApiError, 401 refresh
    errors.ts               ApiError + envelope parsing + friendly messages
    types.ts                contract types
    endpoints.ts            one typed function per Sprint 1 endpoint
    instance.ts             app-wide client instance
  auth/
    tokenStorage.ts         expo-secure-store only (with an in-memory copy)
    authStore.ts            zustand: booting | signedOut | signedIn, me, login/register/logout
    routing.ts              pure onboarding → route rules
    validation.ts           email/password rules mirroring the contract
  features/
    profile/                shared ProfileForm (create + edit), validation, labels
    questionnaire/          progress/resume logic, AutosaveQueue, session store, views
    home/                   PersonalitySnapshot
    boot/                   BootScreen
  components/, theme/       small UI kit on plain StyleSheet
```

### Routing

| State | Route |
|---|---|
| booting | Boot screen (restoring the session; if offline: "Try again" / "Sign out") |
| signedOut | `/login` ⇄ `/register` |
| signedIn, no profile | `/profile-setup` |
| profile, questionnaire incomplete | `/questionnaire` (resumes at the first unanswered required question) |
| complete | `/home` (links to `/profile-edit` and `/questionnaire` for review or retakes) |

`(app)/_layout.tsx` applies these rules to whatever route was requested, so a deep link to
`/home` before onboarding is finished, or to any `(app)` route while signed out, gets redirected.

### Auth and token refresh

- Tokens are stored **only** in `expo-secure-store` (`AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY`: not
  synced or backed up to other devices). They are never written to AsyncStorage and never logged.
- Auth endpoints (`/auth/*`) are sent without an `Authorization` header and never trigger a refresh.
- A 🔒 call that returns `401 TOKEN_EXPIRED` or `401 INVALID_TOKEN` triggers **one** `/auth/refresh`.
  Concurrent 401s share the same refresh promise (single-flight). The original request is then
  retried **once** with the new access token. If another request already rotated the tokens, the
  retry uses those and no second refresh is made.
- If the refresh is rejected (401/403/422), or the retry gets another 401, the client clears
  SecureStore and calls the auth store's failure handler. The store switches to `signedOut` and the
  router moves to `/login` with a short explanation.
- If the refresh fails for a transient reason (network, timeout, 5xx), the session is **kept** and
  the error is surfaced, so a flaky connection doesn't sign the user out.
- `bootstrap()` loads tokens from SecureStore and calls `GET /users/me` (refreshing if needed). It
  routes on `me.onboarding`.

### Questionnaire autosave

Each answer updates local state right away and goes into an `AutosaveQueue`, which sends debounced
batches (at most 100) to `PUT /users/me/questionnaire/answers`. On network, timeout or 5xx errors
it retries with exponential backoff (2s → 30s) and shows "Not saved yet — retrying…". Answers stay
queued until the server confirms them, and a newer answer always replaces an older in-flight one.
If the server returns 422 with `fields`, only the rejected ids are dropped; the user is asked to
answer those again. Answers live in a session-wide zustand store, so they survive leaving the
screen, and the store is cleared on sign-out. Submitting flushes the queue first. A
`QUESTIONNAIRE_INCOMPLETE` response jumps to the earliest missing question.

## Dependencies

| Package | Why |
|---|---|
| `expo`, `react`, `react-native` | SDK 57 runtime |
| `expo-router` (+ `react-native-screens`, `react-native-safe-area-context`, `expo-linking`, `expo-constants`) | File-based navigation; peers required by the router. `expo-constants` also reads `extra` config |
| `react-dom` | Peer of expo-router. Pinned to the same version as `react` so npm can resolve the tree (it would otherwise pull a mismatched version); only used for web |
| `expo-secure-store` | Token storage (Keychain / Keystore) |
| `expo-status-bar` | Status bar style |
| `zustand` | Auth and questionnaire session state (same library as the web client) |
| dev: `jest`, `jest-expo`, `@react-native/jest-preset`, `@types/jest` | Unit tests |
| dev: `eslint`, `eslint-config-expo` | `npx expo lint` |

Date of birth is entered as three labelled number fields (day / month / year), validated as a real
calendar date. That avoids a native date-picker dependency, works in Expo Go, and holds up with
large text sizes and screen readers.

## Checks

```bash
npx tsc --noEmit       # strict type check
npx expo lint
npx jest
npx expo-doctor
npx expo export --platform ios --platform android   # proves both bundles compile (output: dist/, gitignored)
```

When the network blocks `api.expo.dev` or `reactnative.directory`, prefix commands with
`EXPO_OFFLINE=1`. expo-doctor's config-schema and React Native Directory checks need those hosts.
