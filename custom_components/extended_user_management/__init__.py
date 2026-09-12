"""HA Extended User Management: per-person PIN and profile-extension services."""
from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (ATTR_HAS_PIN, ATTR_KEY, ATTR_LOCKED_OUT, ATTR_PERSON_ENTITY_ID,
                    ATTR_PHONE_NUMBER, ATTR_PIN, ATTR_PROFILES, ATTR_VALUE, ATTR_VERIFIED,
                    DOMAIN, SERVICE_CLEAR_PIN, SERVICE_FIND_PERSON_BY_PHONE,
                    SERVICE_GET_PROFILE_VALUE, SERVICE_LIST_PIN_STATUS, SERVICE_SET_PIN,
                    SERVICE_SET_PROFILE_VALUE, SERVICE_VERIFY_PIN)
from .storage import ProfileStore

WWW_URL_PATH = f"/{DOMAIN}_files"

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
# A "simple JSON" value: a scalar, a list of scalars, or a list of flat
# string-keyed records (e.g. important_people: [{"name": ..., "relationship": ...}]).
# Deliberately generic rather than validating specific well-known keys --
# those are a documented convention (see README), not something this
# integration enforces in code.
# cv.boolean must be tried before cv.string: cv.string coerces any non-list/dict
# value via str(value), so a real bool would otherwise always match cv.string
# first and get silently stringified to "True"/"False" instead of staying a bool.
_SCALAR = vol.Any(cv.boolean, cv.string, vol.Coerce(float), None)
_FLAT_RECORD = vol.Schema({cv.string: _SCALAR})
PROFILE_VALUE_SCHEMA = vol.Any(_SCALAR, [_SCALAR], [_FLAT_RECORD])

SET_PROFILE_VALUE_SCHEMA = vol.Schema({
    vol.Required(ATTR_PERSON_ENTITY_ID): PERSON_ENTITY_SCHEMA,
    vol.Required(ATTR_KEY): cv.string,
    vol.Required(ATTR_VALUE): PROFILE_VALUE_SCHEMA,
})
GET_PROFILE_VALUE_SCHEMA = vol.Schema({
    vol.Required(ATTR_PERSON_ENTITY_ID): PERSON_ENTITY_SCHEMA,
    vol.Required(ATTR_KEY): cv.string,
})
FIND_PERSON_BY_PHONE_SCHEMA = vol.Schema({vol.Required(ATTR_PHONE_NUMBER): cv.string})


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

    async def handle_list_pin_status(call: ServiceCall) -> ServiceResponse:
        store = _store_for(call)
        profiles = {
            state.entity_id: {
                ATTR_HAS_PIN: store.has_pin(state.entity_id),
                ATTR_LOCKED_OUT: store.locked_out(state.entity_id),
            }
            for state in hass.states.async_all("person")
        }
        return {ATTR_PROFILES: profiles}

    async def handle_find_person_by_phone(call: ServiceCall) -> ServiceResponse:
        store = _store_for(call)
        return {ATTR_PERSON_ENTITY_ID: store.find_by_phone_number(call.data[ATTR_PHONE_NUMBER])}

    hass.services.async_register(DOMAIN, SERVICE_SET_PIN, handle_set_pin, schema=SET_PIN_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_PIN, handle_clear_pin, schema=CLEAR_PIN_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_VERIFY_PIN, handle_verify_pin,
                                 schema=VERIFY_PIN_SCHEMA, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, SERVICE_SET_PROFILE_VALUE, handle_set_profile_value,
                                 schema=SET_PROFILE_VALUE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_GET_PROFILE_VALUE, handle_get_profile_value,
                                 schema=GET_PROFILE_VALUE_SCHEMA, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, SERVICE_LIST_PIN_STATUS, handle_list_pin_status,
                                 schema=vol.Schema({}), supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, SERVICE_FIND_PERSON_BY_PHONE, handle_find_person_by_phone,
                                 schema=FIND_PERSON_BY_PHONE_SCHEMA,
                                 supports_response=SupportsResponse.ONLY)

    www_path = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(WWW_URL_PATH, str(www_path), True)]
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]:
        for service in (SERVICE_SET_PIN, SERVICE_CLEAR_PIN, SERVICE_VERIFY_PIN,
                        SERVICE_SET_PROFILE_VALUE, SERVICE_GET_PROFILE_VALUE,
                        SERVICE_LIST_PIN_STATUS, SERVICE_FIND_PERSON_BY_PHONE):
            hass.services.async_remove(DOMAIN, service)
    return True
