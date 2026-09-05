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
`set_profile_value`, `get_profile_value`) and storage are implemented;
config flow is a minimal single-instance hub (no dashboard/Lovelace card
yet). Not yet published to HACS.

## Services

| Service | Purpose |
|---|---|
| `extended_user_management.set_pin` | Set/replace a person's PIN. Admin-initiated only — never call this from voice/conversation input. |
| `extended_user_management.clear_pin` | Remove a person's PIN. |
| `extended_user_management.verify_pin` | Check a submitted PIN against a person's stored PIN. Returns `{verified, locked_out}`. |
| `extended_user_management.set_profile_value` | Set an arbitrary extended-profile key/value for a person. |
| `extended_user_management.get_profile_value` | Read an extended-profile key/value for a person. Returns `{value}`. |

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
