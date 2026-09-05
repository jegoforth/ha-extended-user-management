"""PBKDF2-based PIN hashing and verification.

No plaintext PIN is ever persisted. Rate limiting is per person_entity_id
and process-local (reset on Home Assistant restart) -- an acceptable
tradeoff for a low-stakes, short-lived confirmation step rather than a
durable security boundary on its own; the PIN hash itself is the real
protection, the lockout just raises the cost of guessing.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time

from .const import LOCKOUT_SECONDS, MAX_PIN_ATTEMPTS, MAX_PIN_LENGTH, MIN_PIN_LENGTH, PBKDF2_ITERATIONS

_failures: dict[str, list[float]] = {}


def looks_like_pin(value: str) -> bool:
    cleaned = value.strip()
    return cleaned.isdigit() and MIN_PIN_LENGTH <= len(cleaned) <= MAX_PIN_LENGTH


def hash_pin(pin: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, PBKDF2_ITERATIONS)


def new_pin_record(pin: str) -> dict:
    """Produce a storable {salt, hash} record (both hex-encoded) for a PIN."""
    if not looks_like_pin(pin):
        raise ValueError(f"PIN must be {MIN_PIN_LENGTH}-{MAX_PIN_LENGTH} digits")
    salt = os.urandom(16)
    return {"salt": salt.hex(), "hash": hash_pin(pin.strip(), salt).hex()}


def locked_out(person_entity_id: str, *, now: float | None = None) -> bool:
    current = time.time() if now is None else now
    attempts = [t for t in _failures.get(person_entity_id, []) if current - t < LOCKOUT_SECONDS]
    _failures[person_entity_id] = attempts
    return len(attempts) >= MAX_PIN_ATTEMPTS


def _record_failure(person_entity_id: str, *, now: float | None = None) -> None:
    current = time.time() if now is None else now
    _failures.setdefault(person_entity_id, []).append(current)


def clear_failures(person_entity_id: str) -> None:
    _failures.pop(person_entity_id, None)


def verify(person_entity_id: str, submitted_pin: str, record: dict | None, *,
           now: float | None = None) -> bool:
    if locked_out(person_entity_id, now=now):
        return False
    if not looks_like_pin(submitted_pin):
        _record_failure(person_entity_id, now=now)
        return False
    if not isinstance(record, dict) or "salt" not in record or "hash" not in record:
        _record_failure(person_entity_id, now=now)
        return False
    try:
        salt = bytes.fromhex(record["salt"])
        expected = bytes.fromhex(record["hash"])
    except (TypeError, ValueError):
        _record_failure(person_entity_id, now=now)
        return False
    computed = hash_pin(submitted_pin.strip(), salt)
    if hmac.compare_digest(computed, expected):
        clear_failures(person_entity_id)
        return True
    _record_failure(person_entity_id, now=now)
    return False
