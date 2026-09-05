"""Config flow for HA Extended User Management.

Deliberately a single-instance hub with no setup-time fields: there is
nothing to configure at install time. Per-person PIN and profile
management happens afterward via services (and, later, a dashboard),
not during setup -- new household members can be added at any time
without reconfiguring the integration itself.
"""
from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN


class ExtendedUserManagementConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="HA Extended User Management", data={})
        return self.async_show_form(step_id="user")
