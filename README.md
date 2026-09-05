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
the PIN itself), and lets an admin set or clear one inline. PINs never
pass through `hass.states` — only as the immediate payload of a
`set_pin`/`clear_pin` service call — so they never enter the recorder,
history, or logbook.

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
