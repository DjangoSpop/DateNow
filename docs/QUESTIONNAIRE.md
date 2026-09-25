# Questionnaire: audit and `ipip-v1` specification

Owner: AI / Matching. Code: `backend/app/questionnaire/`. Tests: `backend/tests/questionnaire/`.
API shapes: `docs/API_CONTRACT.md` (Questionnaire section) is authoritative. This file documents what the package
does and why.

---

## Part 1: Audit of the legacy implementation

Audited sources: `backend/app/questionnaire_processor.py` (legacy scorer), `frontend/src/data/questionnaireData.ts`
(question bank, reverse flags, client-side `calculateTraitScore`) and `PsychologicalProfile` in `backend/app/models.py`.

### 1.1 What existed

| Section | Ids | Type | Legacy scoring target |
|---|---|---|---|
| Personality | `bf_1`–`bf_44` | 1–5 agree scale | Big Five columns |
| Values | `val_1`–`val_5` | 1–5 scale | one value column each |
| | `val_6` | single choice (5) | `family_orientation` (with `val_1`) |
| | `val_7` | single choice (5) | none (trait `lifestyle`, no column) |
| Love languages | `ll_1`–`ll_5` | 1–5 scale | one `love_language_*` column each |
| Communication | `comm_1` | single choice (4) | `communication_style` |
| | `comm_2` | single choice (4) | `conflict_resolution` |
| | `comm_3` | single choice (4) | none |
| Attachment | `att_1`–`att_4` | 1–5 scale | `attachment_style` (partly, see below) |
| | `att_5` | single choice (4) | `attachment_style` |
| Goals | `rg_1`, `rg_2` | single choice | none |
| Preferences | `pref_1`–`pref_3` | 1–5 scale | none |
| | `pref_4`, `pref_5` | single choice | none |
| Verification | `verify_1`, `verify_2` | free text | `verify_authenticity()` (bot check) |

Inputs: the frontend stored answers as `{question_id: number | option label string | free text}`. Outputs of
`process_questionnaire`: a dict of the 18 profile columns plus `questionnaire_responses`.

### 1.2 Big Five item mapping and reverse keys

The 44 `bf_*` items are **not** the BFI-44 (the frontend comment says "validated BFI-44"). They are 44 of the 50
**IPIP Big-Five Factor Markers** (Goldberg, 1992), items taken verbatim:

| Trait (column) | Items | Minus-keyed (reverse) | IPIP items not used |
|---|---|---|---|
| extraversion | `bf_1`–`bf_8` | `bf_2`, `bf_4`, `bf_6`, `bf_8` | "I don't mind being the center of attention" (+), "I am quiet around strangers" (−) |
| agreeableness | `bf_9`–`bf_18` | `bf_9`, `bf_11`, `bf_13`, `bf_15` | none (all 10) |
| conscientiousness | `bf_19`–`bf_28` | `bf_20`, `bf_22`, `bf_24`, `bf_26` | none (all 10) |
| neuroticism | `bf_29`–`bf_36` | `bf_30`, `bf_32` | "I get irritated easily" (+), "I often feel blue" (+) |
| openness (IPIP "Intellect/Imagination") | `bf_37`–`bf_44` | `bf_38`, `bf_40`, `bf_42` | "I use difficult words" (+), "I am full of ideas" (+) |

Neuroticism is scored in the neuroticism direction (IPIP keys factor IV as Emotional Stability; the signs above are
flipped accordingly: "I am relaxed most of the time" and "I seldom feel blue" are the reverse items).

**Reverse-key check result:** every item's wording was checked against the published IPIP key. The frontend
`reverse` flags and the legacy processor's per-trait `is_reverse` maps agree with each other and with IPIP for all 44
items. No reverse-key mismatches were found. The new bank keeps exactly these keys, and a test pins them.

Consequence of the trimmed item set: E, N and O have 8 items with an unbalanced forward/reverse mix (E 4/4, N 6/2,
O 5/3; A and C 6/4). This is acceptable for Sprint 1 but means a pure acquiescent responder (all 5s) scores
N = 75, O = 62.5, A = C = 60, E = 50 rather than 50 everywhere. The scores are not normed.

### 1.3 Defects found

Legacy scorer (`questionnaire_processor.py`):

1. **Never called.** Nothing imported it. Scores were computed client-side (`calculateTraitScore`) and sent to
   `POST /users/me/psychological-profile`, so a client could write arbitrary scores.
2. **Score range bug.** `(avg / 5) * 100` maps a 1–5 mean to **20–100**, not 0–100. The same bug is in the frontend
   `calculateTraitScore`, the value scale items and the love-language items.
3. **Mixed ranges inside one score.** `family_orientation` averaged `val_1` (20–100) with `val_6` mapped to 0–100.
4. **Missing answers skipped silently.** A trait with no answers returned `0.0`, which cannot be told apart from a real
   minimum score. Partial answers were scored on whatever subset existed.
5. **No input validation.** Out-of-range numbers (0, 7, −3) were used as given. `True`/`False` count as ints in
   Python, and floats passed through. An unknown `val_6` string silently became 50.
6. **`communication_style` was raw label text.** It returned `responses['comm_1']` verbatim, e.g.
   `"Direct and straightforward"`, not a vocabulary value. Any string, including user-controlled ones, was stored.
   The default when unanswered was `"diplomatic"`, a made-up answer.
7. **`conflict_resolution` used substring matching** on label text (`'directly'`, `'time'`, `'compromise'`, `'avoid'`).
   This breaks on any wording change or translation, crashes (`AttributeError`) on non-string input, and defaulted
   to `"collaborative"` when unanswered. The output vocabulary (`direct`, `reflective`, `collaborative`, `avoidant`)
   does not match the model comment (`avoidant, collaborative, competitive`).
8. **Weak attachment logic.**
   - `att_5` short-circuited the rule. Because every user answers it, the scale items were never used in practice.
   - Through `att_5`, "Be very close", "Maintain some independence" and "It depends" all returned `secure`, and only
     "Keep emotional distance" returned `avoidant`. `anxious` and `fearful-avoidant` could never be produced.
   - `att_3` and `att_4` were never read, even in the fallback.
   - In the fallback, every mid-range answer (for example all 3s) was labelled `fearful-avoidant`, which is backwards.
   - Substring matching on label text again (`'very close'`, `'independence'`, `'distance'`).
9. **`questionnaire_responses` aliased the input dict** (same object, not a copy).
10. **Wrong scale labels in the UI.** Every scale question showed "Strongly Disagree … Strongly Agree", including the
    "How important is …?" questions (`val_1`, `val_2`, `val_4`, `val_5`, `pref_1`–`pref_3`) and "How much do you
    value …?" (`val_3`).

Questions that were collected but never scored: `val_7`, `comm_3`, `att_3`, `att_4` (and in practice `att_1`,
`att_2`), `rg_1`, `rg_2`, `pref_1`–`pref_5`. `rg_1` overlaps with the profile's `relationship_goal` enum.

### 1.4 `verify_*` "authenticity" check: excluded

`verify_1` ("What brings you to DateNow?") and `verify_2` ("Describe your ideal first date") were free text checked by
`verify_authenticity()`: at least 20 characters, not all caps, and containing one of ten English stop-words.

We recommend removing it, and `ipip-v1` removes it:

- **It does not detect bots.** Any script, and any text generator, passes it trivially.
- **It rejects real people.** Non-English answers, short answers and all-caps typists fail.
- **It collects sensitive free text for no benefit.** Dating-intent and first-date narratives are personal data that
  would be stored in `questionnaire_responses` and possibly sent to AI services.
- Real abuse controls (rate limiting, email/phone verification, behaviour signals) belong in the auth/trust layer,
  not in the personality questionnaire.

`verify_*` ids are rejected as unknown by `validate_answers`.

---

## Part 2: `ipip-v1` specification (`backend/app/questionnaire/`)

### 2.1 Package layout and interface

- `bank.py` holds the question bank (single source of truth), including the scoring keys, which are never exposed.
- `validation.py` holds `AnswerValidationError`, `get_definition`, `question_ids`, `total_required`,
  `validate_answers` and `missing_required`.
- `scoring.py` holds `score` and the vocabularies.
- `__init__.py` re-exports the public interface.
- `app/questionnaire_processor.py` is now a deprecated shim that re-exports the new API. `process_questionnaire` is an
  alias of `score`, and `verify_authenticity` is removed. Nothing imported the old module.

Everything uses only the standard library: no database, FastAPI or I/O.

```python
QUESTIONNAIRE_VERSION = "ipip-v1"
class AnswerValidationError(ValueError): errors: dict[str, str]   # question_id -> message
get_definition() -> dict          # GET /questionnaire body; fresh copy each call
question_ids() -> list[str]       # presentation order
total_required() -> int           # 71
validate_answers(answers) -> dict # partial OK; normalized copy in presentation order
missing_required(answers) -> list[str]   # absent or None, presentation order
score(answers) -> dict            # complete + valid only; PsychologicalProfile columns
```

### 2.2 Question bank

There are 71 questions, all required, in 7 sections:

| Section | Questions |
|---|---|
| personality | `bf_1`–`bf_44` |
| values | `val_1`–`val_7` |
| love | `ll_1`–`ll_5` |
| communication | `comm_1`–`comm_3` |
| attachment | `att_1`–`att_5` |
| goals | `rg_1`, `rg_2` |
| preferences | `pref_1`–`pref_5` |

Ids and texts are unchanged from the frontend. The `verify` section is removed.

- Scale questions are 1–5 with all five labels. The "How important" items use importance labels ("Not at all
  important" … "Extremely important"), `val_3` uses amount labels ("Not at all" … "Very much"), and all other scale
  items use agree labels.
- Single-choice options keep the existing label text and gain a stable snake_case `value`:

| Question | value → label |
|---|---|
| `val_6` | `definitely`, `probably`, `not_sure`, `probably_not`, `definitely_not` |
| `val_7` | `outdoor_adventures`, `cultural_events`, `relaxing_at_home`, `social_gatherings`, `personal_projects` |
| `comm_1` | `direct`, `diplomatic`, `emotional`, `logical` |
| `comm_2` | `address_directly`, `cool_down_first`, `seek_compromise`, `avoid_confrontation` |
| `comm_3` | `work_together`, `take_turns`, `discuss_feelings`, `space_then_reconnect` |
| `att_5` | `very_close`, `some_independence`, `keep_distance`, `depends` |
| `rg_1` | `serious`, `see_where_it_goes`, `casual`, `friendship` |
| `rg_2` | `ready_now`, `within_a_year`, `in_a_few_years`, `not_sure`, `not_settling_down` |
| `pref_4` | `deal_breaker`, `concern`, `not_ideal_but_okay`, `not_an_issue` |
| `pref_5` | `never`, `rarely`, `socially`, `regularly`, `prefer_not_to_say` |

The labels are listed in the same order in `bank.py`. Clients must send `value`, never `label`.

### 2.3 Validation

`validate_answers` checks every entry and raises one `AnswerValidationError` listing **every** bad id:

- unknown id, including `verify_*` and non-string keys: `"unknown question id"`
- scale answer that is a `bool`: `"must be an integer, not a boolean"`
- scale answer that is not an `int` (float, including `4.0`, numeric string, `None`, list): type error
- scale answer outside 1–5: range error
- choice answer that is not one of the option `value`s (labels, wrong case, ints, `None`): invalid option
- a non-dict `answers` argument: error keyed `"answers"`

`score` additionally reports every required id that is missing as `"required"`, together with any invalid ids, in
one error. This matches `QUESTIONNAIRE_INCOMPLETE` / `VALIDATION_ERROR` `fields`.

### 2.4 Scoring rules

All numeric outputs are 0–100, rounded **half-up** to 1 decimal (31.25 → 31.3, as in the contract example). The
computation uses exact fractions, so the result does not depend on float summation order or on the input key order.

- **Scale transform (changed):** `(mean − 1) / 4 × 100`, so 1 → 0, 3 → 50, 5 → 100. It replaces the legacy
  `(mean / 5) × 100`, which gave 20–100.
- **Reverse items:** `6 − x` before averaging (keys listed in §1.2).
- **Big Five:** the mean of the keyed items per trait, then the scale transform.
- **Values:**
  - `career_ambition` = `val_2`, `adventure_seeking` = `val_3`, `social_consciousness` = `val_4` and
    `spiritual_religious` = `val_5`, each through the scale transform.
  - `family_orientation` = the mean of `val_1` (transformed) and `val_6` via this table: `definitely` 100,
    `probably` 75, `not_sure` 50, `probably_not` 25, `definitely_not` 0.
- **Love languages:** `love_language_words/acts/gifts/time/touch` = `ll_1`…`ll_5` through the scale transform. They
  are single items, so treat them as rough signals.

**Categorical vocabularies:**

| Column | Vocabulary | Rule |
|---|---|---|
| `communication_style` | `direct`, `diplomatic`, `emotional`, `logical` | `comm_1` value (1:1) |
| `conflict_resolution` | `direct`, `reflective`, `collaborative`, `avoidant` | `comm_2`: `address_directly`→`direct`, `cool_down_first`→`reflective`, `seek_compromise`→`collaborative`, `avoid_confrontation`→`avoidant` |
| `attachment_style` | `secure`, `anxious`, `avoidant`, `fearful_avoidant` | see below |

Note: `fearful_avoidant` uses an underscore, where the legacy model comment used a hyphen.

**Attachment (a coarse heuristic, not a clinical assessment).** It uses two dimensions on the 1–5 scale, following
the anxiety/avoidance model:

- `anxiety` = mean(`att_2`, `att_4`)
- `avoidance` = mean(6 − `att_1`, 6 − `att_3`)
- Anxiety is **high** when `anxiety > 3`.
- Avoidance is **high** when `avoidance > 3`, or when `avoidance == 3` exactly and `att_5 == keep_distance`. `att_5`
  only breaks a tie at the midpoint; it never overrides the scale items.
- The result is: low/low → `secure`, high anxiety only → `anxious`, high avoidance only → `avoidant`, both high →
  `fearful_avoidant`.

Four items cannot support a reliable classification. Use the label for conversation hints only, never as a hard
matching filter or something shown to users as a diagnosis.

**Collected but not yet scored:** `val_7`, `comm_3`, `rg_1`, `rg_2` and `pref_1`–`pref_5` are required and validated,
and they are stored in `questionnaire_responses`, but they do not affect any column. Sprint 2 normalizes them into
proper fields; `rg_1` overlaps with `Profile.relationship_goal` and should be reconciled then.

**`questionnaire_responses`** is a new dict holding the normalized answers in presentation order. Mutating the input
or the output afterwards does not affect the other.

**Determinism:** `score` is a pure function with no randomness, clock or I/O. The same answers always give an
identical result.

### 2.5 Versioning

Any change to ids, options, keys or formulas must bump `QUESTIONNAIRE_VERSION`. Stored profiles carry the version
they were scored with.
