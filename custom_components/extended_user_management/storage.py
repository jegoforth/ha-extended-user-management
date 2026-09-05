"""Persistence for per-person extended profiles.

Schema (version 1)::

    {
        "profiles": {
            "<person_entity_id>": {
                "pin": {"salt": "<hex>", "hash": "<hex>"} | null,
                "extra": {"<key>": <value>, ...}
            },
            ...
        }
    }

Each person's record is independent; the `pin` sub-record is only ever a
salt+hash pair (see pin.py), never a plaintext value. `extra` is
deliberately open-ended -- it is the extension point for whatever profile
data gets added later without a schema migration each time.
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from . import pin as pin_module
from .const import STORAGE_KEY, STORAGE_VERSION


def _empty_profile() -> dict:
    return {"pin": None, "extra": {}}


class ProfileStore:
    def __init__(self, hass: HomeAssistant):
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict = {"profiles": {}}

    async def async_load(self) -> None:
        loaded = await self._store.async_load()
        if isinstance(loaded, dict) and isinstance(loaded.get("profiles"), dict):
            self._data = loaded

    async def _async_save(self) -> None:
        await self._store.async_save(self._data)

    def _profile(self, person_entity_id: str) -> dict:
        return self._data["profiles"].setdefault(person_entity_id, _empty_profile())

    async def async_set_pin(self, person_entity_id: str, new_pin: str) -> None:
        record = pin_module.new_pin_record(new_pin)
        self._profile(person_entity_id)["pin"] = record
        pin_module.clear_failures(person_entity_id)
        await self._async_save()

    async def async_clear_pin(self, person_entity_id: str) -> None:
        self._profile(person_entity_id)["pin"] = None
        pin_module.clear_failures(person_entity_id)
        await self._async_save()

    def has_pin(self, person_entity_id: str) -> bool:
        return self._data["profiles"].get(person_entity_id, {}).get("pin") is not None

    def verify_pin(self, person_entity_id: str, submitted_pin: str) -> bool:
        record = self._data["profiles"].get(person_entity_id, {}).get("pin")
        return pin_module.verify(person_entity_id, submitted_pin, record)

    def locked_out(self, person_entity_id: str) -> bool:
        return pin_module.locked_out(person_entity_id)

    async def async_set_value(self, person_entity_id: str, key: str, value) -> None:
        self._profile(person_entity_id)["extra"][key] = value
        await self._async_save()

    def get_value(self, person_entity_id: str, key: str, default=None):
        return self._data["profiles"].get(person_entity_id, {}).get("extra", {}).get(key, default)
