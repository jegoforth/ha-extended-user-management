# HA Extended User Management

A general-purpose Home Assistant integration for attaching extended profile
data to your existing `person` entities — starting with a hashed PIN,
designed to grow to arbitrary profile fields other integrations or
automations can read and write.

## Why

Home Assistant's `person` entities identify *who* lives in your household,
but there's no built-in way to attach durable, per-person data beyond
presence tracking — no PIN for a voice assistant to confirm "yes, that's
actually Shelley" before doing something consequential, no general-purpose
place to store a household member's preferences that other integrations
could read.

This fills that gap as its own building block: it doesn't do anything
voice-, lock-, or automation-specific itself. It's the layer other
integrations call into.

Known consumer: [Twilio Voice Assistant](https://github.com/jegoforth/twilio_voice_assistant)
uses `find_person_by_phone` to match incoming callers, and relies on this
integration entirely for phone number and PIN storage -- it is a required
prerequisite for that App as of its current release.

## Status

Early scaffold. Core services (`set_pin`, `verify_pin`, `clear_pin`,
`set_profile_value`, `get_profile_value`, `list_pin_status`) and storage
are implemented, along with a Lovelace admin card for managing PINs.
Config flow is a minimal single-instance hub. Not yet published to HACS,
and not yet tested against a real Home Assistant instance.

## Services

| Service | Purpose |
|---|---|
| `extended_user_management.set_pin` | Set/replace a person's PIN. Admin-initiated only — never call this from voice/conversation input. |
| `extended_user_management.clear_pin` | Remove a person's PIN. |
| `extended_user_management.verify_pin` | Check a submitted PIN against a person's stored PIN. Returns `{verified, locked_out}`. |
| `extended_user_management.set_profile_value` | Set an arbitrary extended-profile key/value for a person. |
| `extended_user_management.get_profile_value` | Read an extended-profile key/value for a person. Returns `{value}`. |
| `extended_user_management.list_pin_status` | List every person entity with whether a PIN is set and whether they're locked out. Returns `{profiles: {<person_entity_id>: {has_pin, locked_out}}}`. |
| `extended_user_management.find_person_by_phone` | Reverse-lookup which person has a given phone number set (via `phone_number` profile key). Returns `{person_entity_id}` (`null` if no match). |

## Dashboard card

The integration serves `extended-user-management-card.js` itself (no HACS
frontend-resource registration needed) at:

```
/extended_user_management_files/extended-user-management-card.js
```

To use it:

1. Settings → Dashboards → ⋮ (top right) → Resources → Add Resource.
2. URL: the path above. Resource type: JavaScript Module.
3. Add a card to any dashboard, type `Custom: Extended User Management` (or
   add manually via YAML: `type: custom:extended-user-management-card`).

The card lists every `person` entity, shows whether a PIN is set (never
the PIN itself), and lets an admin set or clear one inline. It also has a
plain phone-number field per person (the `phone_number` well-known profile
key, see below) for anything that matches callers by number, such as
`find_person_by_phone`. PINs never pass through `hass.states` — only as
the immediate payload of a `set_pin`/`clear_pin` service call — so they
never enter the recorder, history, or logbook. Phone numbers are ordinary
profile data, not a secret, so they round-trip through `get_profile_value`/
`set_profile_value` and are shown in the field.

## Well-known profile keys

`set_profile_value`/`get_profile_value` accept any key — this is a
documented convention for interoperability between consumers (Elspeth,
someone else's HA Assist automation, whatever), not something enforced in
code. Using these names where they fit means multiple integrations can
share the same household context instead of each inventing its own
vocabulary.

Values may be a scalar (string/boolean/number), a list of scalars, or a
list of flat string-keyed records (for `important_people`).

| Key | Type | Example | Notes |
|---|---|---|---|
| `phone_number` | string | `"+15551234567"` | E.164 recommended for exact-match reverse lookup via `find_person_by_phone` (e.g. matching a Twilio caller ID) |
| `sms_opted_in` | boolean | `true` | Real consent state for outbound SMS via this person's `phone_number` -- set only by an inbound-SMS webhook when the person's own phone sends a recognized opt-in/opt-out keyword (e.g. YES/START/STOP), never by a consuming integration on their behalf |
| `preferred_name` | string | `"Shell"` | How they like to be addressed, distinct from the `person` entity's formal name |
| `gender` | string | `"female"` | Free text, not a restricted enum — how a consuming integration uses this (e.g. pronoun selection) is its own decision, not part of this convention |
| `occupation` | string | `"software engineer"` | |
| `work_schedule` | string | `"remote, flexible hours"` | Free text, not structured — too varied to force into a schema |
| `communication_style` | string | `"concise, direct recommendations"` | Useful to *any* conversation agent, not just Elspeth |
| `hobbies` | list[string] | `["gardening", "chess"]` | |
| `interests` | list[string] | `["Scottish history", "true crime podcasts"]` | Broader than hobbies — topics they like discussing |
| `food_preferences` | list[string] | `["spicy food", "whole grains"]` | |
| `food_restrictions` | list[string] | `["no nuts", "vegetarian"]` | Allergies/diet — household-relevant, not medical-sensitivity data |
| `restaurant_likes` | list[string] | `["Chick-fil-A"]` | Specific restaurants/chains enjoyed — distinct from `food_preferences` (cuisine/food types) and `food_restrictions` (dietary/allergy, not taste) |
| `restaurant_dislikes` | list[string] | `["Burger King"]` | Specific restaurants/chains to avoid, same distinction as `restaurant_likes` |
| `music_preferences` | list[string] | `["Fleetwood Mac", "classic rock"]` | |
| `entertainment_preferences` | list[string] | `["Outlander", "true crime documentaries"]` | |
| `important_people` | list[{name, relationship}] | `[{"name": "Grace", "relationship": "daughter"}]` | The one structured key |
| `daily_routines` | string | `"morning run around 6am"` | |
| `travel_preferences` | list[string] | `["historical sites", "quiet beach towns"]` | |
| `current_focus` | string | `"planning a kitchen renovation"` | What's got their attention lately — deliberately not durable/permanent-feeling |

This store is for household-shared, non-sensitive context by convention.
Genuinely personal or sensitive facts belong in whatever
tighter-controlled, conversation-gated memory system a consuming
integration already has — not here.

## Security notes

- PINs are never stored in plaintext — PBKDF2-HMAC-SHA256, 200,000
  iterations, a random salt per PIN.
- Verification is rate-limited per person (3 attempts / 5 minutes,
  process-local — resets on a Home Assistant restart). This raises the
  cost of guessing; the hash itself is the real protection, not the
  lockout.
- `verify_pin` is the only service meant to be called from untrusted
  conversational input. `set_pin`/`clear_pin` should only ever be
  triggered by an authenticated admin action.

## Development

```bash
python -m unittest discover -s tests
```

`tests/test_pin.py` runs standalone (no Home Assistant install required —
`pin.py` has zero Home Assistant dependencies). Testing `storage.py` and
`config_flow.py` against a real Home Assistant instance is a planned
follow-up (likely via `pytest-homeassistant-custom-component`).

## License

MIT — see [LICENSE](LICENSE).
