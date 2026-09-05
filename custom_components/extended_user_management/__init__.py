"""HA Extended User Management: per-person PIN and profile-extension services."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (ATTR_KEY, ATTR_LOCKED_OUT, ATTR_PERSON_ENTITY_ID, ATTR_PIN, ATTR_VALUE,
                    ATTR_VERIFIED, DOMAIN, SERVICE_CLEAR_PIN, SERVICE_GET_PROFILE_VALUE,
                    SERVICE_SET_PIN, SERVICE_SET_PROFILE_VALUE, SERVICE_VERIFY_PIN)
from .storage import ProfileStore

PLATFORMS: list[str] = []

PERSON_ENTITY_SCHEMA = cv.entity_domain("person")

SET_PIN_SCHEMA = vol.Schema({
    vol.Required(ATTR_PERSON_ENTITY_ID): PERSON_ENTITY_SCHEMA,
    vol.Required(ATTR_PIN): cv.string,
})
CLEAR_PIN_SCHEMA = vol.Schema({vol.Required(ATTR_PERSON_ENTITY_ID): PERSON_ENTITY_SCHEMA})
VERIFY_PIN_SCHEMA = vol.Schema({
    vol.Required(ATTR_PERSON_ENTITY_ID): PERSON_ENTITY_SCHEMA,
    vol.Required(ATTR_PIN): cv.string,
})
SET_PROFILE_VALUE_SCHEMA = vol.Schema({
    vol.Required(ATTR_PERSON_ENTITY_ID): PERSON_ENTITY_SCHEMA,
    vol.Required(ATTR_KEY): cv.string,
    vol.Required(ATTR_VALUE): vol.Any(cv.string, cv.boolean, vol.Coerce(float), None),
})
GET_PROFILE_VALUE_SCHEMA = vol.Schema({
    vol.Required(ATTR_PERSON_ENTITY_ID): PERSON_ENTITY_SCHEMA,
    vol.Required(ATTR_KEY): cv.string,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = ProfileStore(hass)
    await store.async_load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = store

    def _store_for(_call: ServiceCall) -> ProfileStore:
        # Single config entry is the expected/supported shape for v1.
        return next(iter(hass.data[DOMAIN].values()))

    async def handle_set_pin(call: ServiceCall) -> None:
        store = _store_for(call)
        try:
            await store.async_set_pin(call.data[ATTR_PERSON_ENTITY_ID], call.data[ATTR_PIN])
        except ValueError as exc:
            raise HomeAssistantError(str(exc)) from exc

    async def handle_clear_pin(call: ServiceCall) -> None:
        await _store_for(call).async_clear_pin(call.data[ATTR_PERSON_ENTITY_ID])

    async def handle_verify_pin(call: ServiceCall) -> ServiceResponse:
        store = _store_for(call)
        person_entity_id = call.data[ATTR_PERSON_ENTITY_ID]
        return {
            ATTR_VERIFIED: store.verify_pin(person_entity_id, call.data[ATTR_PIN]),
            ATTR_LOCKED_OUT: store.locked_out(person_entity_id),
        }

    async def handle_set_profile_value(call: ServiceCall) -> None:
        await _store_for(call).async_set_value(
            call.data[ATTR_PERSON_ENTITY_ID], call.data[ATTR_KEY], call.data[ATTR_VALUE]
        )

    async def handle_get_profile_value(call: ServiceCall) -> ServiceResponse:
        store = _store_for(call)
        value = store.get_value(call.data[ATTR_PERSON_ENTITY_ID], call.data[ATTR_KEY])
        return {ATTR_VALUE: value}

    hass.services.async_register(DOMAIN, SERVICE_SET_PIN, handle_set_pin, schema=SET_PIN_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_PIN, handle_clear_pin, schema=CLEAR_PIN_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_VERIFY_PIN, handle_verify_pin,
                                 schema=VERIFY_PIN_SCHEMA, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, SERVICE_SET_PROFILE_VALUE, handle_set_profile_value,
                                 schema=SET_PROFILE_VALUE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_GET_PROFILE_VALUE, handle_get_profile_value,
                                 schema=GET_PROFILE_VALUE_SCHEMA, supports_response=SupportsResponse.ONLY)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        for service in (SERVICE_SET_PIN, SERVICE_CLEAR_PIN, SERVICE_VERIFY_PIN,
                        SERVICE_SET_PROFILE_VALUE, SERVICE_GET_PROFILE_VALUE):
            hass.services.async_remove(DOMAIN, service)
    return True
