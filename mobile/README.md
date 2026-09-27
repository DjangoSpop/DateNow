# DateNow Mobile

React Native app for DateNow AI, built with Expo (SDK 57), TypeScript (strict) and expo-router.
It is built strictly against `docs/API_CONTRACT.md`, the Sprint 1 contract.

Sprint 1 covers:

- boot/session restore
- login, register and logout
- profile setup
- the server-driven onboarding questionnaire, with draft save and resume
- a home screen that shows the server-computed psychological profile

## Setup

```bash
cd mobile
npm install
npm start            # Expo dev server (press i / a, or scan the QR code)
```

Native dependencies are pinned to SDK 57 versions. Add new native packages with
`npx expo install <pkg>`, not `npm install`, so their versions match the SDK.

| Script | What it does |
|---|---|
| `npm start` | Start Metro / Expo dev server |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | `expo lint` (eslint-config-expo, flat config) |
| `npm test` | Unit tests (jest-expo) |
| `npm run doctor` | `expo-doctor` (needs internet access to api.expo.dev / reactnative.directory) |
| `npm run export:android` / `export:ios` | Production JS bundle, proving the app compiles |

The app uses only Expo SDK modules (`expo-router`, `expo-secure-store`, `expo-splash-screen`,
`expo-constants`), AsyncStorage and zustand. All of them are included in **Expo Go**, so no custom
dev build is needed for Sprint 1.

## Configuration

Configuration is read by `app.config.ts` at bundle time and exposed via `expo-constants` `extra`.
The runtime resolver in `src/config/env.ts` adds `/api/v1`.

| Variable | Default | Notes |
|---|---|---|
| `EXPO_PUBLIC_API_URL` | *(unset)* | Backend **origin** without `/api/v1`, e.g. `https://api.datenow.app`. |
| `APP_ENV` | `development` | `development` \| `preview` \| `production` |

- **Development, no URL set:** iOS simulator and web use `http://localhost:8000`. The Android emulator uses
  `http://10.0.2.2:8000`, because the emulator's `localhost` is the emulator itself.
- **Production:** `EXPO_PUBLIC_API_URL` is **required** and **must be `https://`**. `app.config.ts` throws
  during the build otherwise, and the runtime resolver checks again.

See `.env.example`. `EXPO_PUBLIC_*` values are embedded in the JS bundle, so never put secrets in them.

## Running against the local backend

Start the backend first (see the repo root `DEVELOPMENT.md`), listening on port 8000.

| Target | Command | API URL used |
|---|---|---|
| iOS simulator (macOS) | `npm run ios` | `http://localhost:8000` (default) |
| Android emulator | `npm run android` | `http://10.0.2.2:8000` (default) |
| Physical device (Expo Go, same Wi-Fi) | `EXPO_PUBLIC_API_URL=http://<LAN-IP>:8000 npm start` | your computer's LAN IP |

For a physical device, the backend must listen on `0.0.0.0` (e.g. `uvicorn app.main:app --host 0.0.0.0 --port 8000`)
and your firewall must allow port 8000. Expo Go and debug builds allow cleartext HTTP to LAN addresses.
Release builds generally do not (Android `usesCleartextTraffic`, iOS ATS), which is another reason
production requires https.

Restart Metro with `npx expo start -c` after changing env vars, because the values are inlined at bundle time.

## Architecture

```
src/
  app/                    expo-router routes (file-based)
    _layout.tsx           boot state machine, splash handling, Stack.Protected route guards
    index.tsx             redirects to the area chosen by resolveBootRoute
    (auth)/login.tsx, register.tsx
    profile-setup.tsx     POST /users/me/profile
    onboarding.tsx        GET /questionnaire + GET/PUT /onboarding + POST /questionnaire/submit
    home.tsx              GET /users/me/psychological-profile
  api/
    client.ts             fetch client: base URL, timeout, bearer, ApiError, 401→refresh→retry
    errors.ts             ApiError + FastAPI {detail} parsing
    types.ts              contract types
    auth.ts, profile.ts, questionnaire.ts, onboarding.ts   typed endpoint functions
  auth/
    tokenStorage.ts       SecureStore-only token persistence
    session.ts            in-memory token cache backed by tokenStorage
  state/authStore.ts      zustand store: boot/login/register/logout/refreshMe
  navigation/bootRoute.ts pure resolveBootRoute(session, me)
  onboarding/             draft mirror (AsyncStorage) + pure resume/validation helpers
  utils/profileForm.ts    profile form validation (18+, ranges) and request mapping
  components/             UI primitives and question renderers
```

### Boot flow

1. The native splash stays up (`SplashScreen.preventAutoHideAsync`) while tokens are read from SecureStore.
2. If tokens exist, the app calls `GET /auth/me`. On a 401 the client refreshes once and retries.
3. `resolveBootRoute(session, me)` picks the next screen:
   - no session: `auth`
   - `!has_profile`: `profile-setup`
   - onboarding not completed: `onboarding`
   - otherwise: `home`
4. The root `Stack` wraps each area in `Stack.Protected guard={route === …}`, so a stale or deep-linked
   screen can't be shown. After a state change (login, profile created, submit, logout, session expiry)
   the layout calls `router.replace` to the new area.
5. A network or server error during boot shows a **retry** screen and keeps the tokens. Only an auth
   failure (refresh rejected) logs the user out.

### API client

- Every request has a timeout (default 15s, 30s for submit) enforced with `AbortController`.
- Every failure becomes a structured `ApiError {status, code, message, fieldErrors?, issues?}`, where `code`
  is one of `network | timeout | unauthorized | validation | conflict | not_found | server | unknown`.
  - FastAPI `detail: string` becomes the `message`.
  - `detail: [{loc,msg}]` becomes `fieldErrors` keyed by the last `loc` segment.
  - The questionnaire endpoints' `detail: [{question_id, message}]` is also parsed. `question_id: "__all__"`
    means a whole-body error.
- A 401 on an authenticated call triggers a **single-flight** `POST /auth/refresh`: concurrent 401s share
  one refresh, then the request is retried once. If the refresh is rejected, or the retry is still 401,
  the session is cleared and the app returns to login. A refresh that fails for **network** reasons keeps
  the session, because the user is probably just offline.
- Unauthenticated endpoints (login, register, refresh) never trigger a refresh.

### Onboarding

- Questions come **only** from `GET /questionnaire`. The app hardcodes no questions and does no scoring.
  It submits raw answers, and the server computes the profile.
- Sections are shown one at a time with a progress bar and Back/Next. Supported question types are
  scale (min…max with labels), single_choice, multiple_choice and text (with a `max_length` counter).
- Drafts are saved with `PUT /onboarding`:
  - debounced 1.5s while answering
  - immediately when changing section, with `current_section` set to the section being entered
  - serialized, so the server always ends up with the latest section
- Every change is mirrored to AsyncStorage (`datenow.onboardingDraft.<userId>`, non-sensitive) with a
  `pendingSync` flag.
  - If a save fails for network reasons, the UI says "Saved on device" and the next save retries.
  - On resume, server state wins unless the local copy has unsynced changes, which are then layered on
    top and pushed.
- The review step shows per-section completion. Submit (`POST /questionnaire/submit`) sends the answers.
  If it returns 422, the app extracts the question ids, highlights them and jumps to the first section
  containing one. A 409 (already completed) refreshes `/auth/me`, which routes to home.

## Security notes

- **Tokens live only in `expo-secure-store`** (iOS Keychain with `AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY`;
  on Android, encrypted with an Android Keystore key). Tokens never go to AsyncStorage and are never logged.
  The app has no `console.*` calls.
- **Web:** SecureStore is unavailable, so tokens are kept **in memory only** and are lost on reload.
  The app deliberately never falls back to `localStorage`. Web is a development convenience, not a
  supported auth target.
- AsyncStorage holds only the onboarding draft mirror. Logout clears tokens, the in-memory user and **all**
  cached drafts. When the session expires (refresh rejected), tokens are cleared but the user's draft is kept.
- There is no server logout / token revocation endpoint in the Sprint 1 contract, so logout is local only.
  A stolen refresh token stays valid until it expires (7 days by default).
- Production builds refuse non-https API URLs.
- Server-controlled profile fields are never sent. The profile body contains only contract fields, and
  empty optional fields are omitted.

## Tests

`npm test` runs jest-expo unit tests in `__tests__/`:

- `client.test.ts`:
  - bearer injection
  - timeout → `timeout` code
  - network → `network` code
  - FastAPI and questionnaire 422 parsing
  - status → code mapping
  - 401 → refresh → retry
  - refresh rejected → session cleared
  - retry still 401 → cleared
  - offline refresh keeps the session
  - single-flight refresh
  - no refresh for login
- `tokenStorage.test.ts`: tokens go through SecureStore (mocked) and never through AsyncStorage.
- `bootRoute.test.ts`: every branch of `resolveBootRoute`.
- `authStore.test.ts`:
  - boot with/without tokens
  - offline boot → retry state
  - unauthorized boot → logged out
  - logout clears tokens and drafts
  - login flow
- `onboardingLogic.test.ts`: resume merging, sanitising stale answers, required checks, 422 id extraction.
- `profileForm.test.ts`: 18+ boundary, date parsing, min ≤ max, request body mapping.
- `env.test.ts`: dev defaults (10.0.2.2 on Android), `/api/v1` handling, production https requirement.

## Known limitations (Sprint 1)

- Date of birth is a `YYYY-MM-DD` text field. No native date picker was added, to avoid a native dependency.
- No NetInfo: "offline" is inferred from failed requests, not detected proactively.
- No photo upload, no profile editing screen (PATCH is typed but unused) and no questionnaire re-take.
- The PUT `/onboarding` merge semantics give no way to *remove* a saved answer. The client only sends
  answered values, so a cleared optional answer stays saved on the server.
- Not yet verified end-to-end against the live backend; that check is part of integration.
