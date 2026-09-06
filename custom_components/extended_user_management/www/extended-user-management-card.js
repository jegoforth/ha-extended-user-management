/**
 * Lovelace card for HA Extended User Management.
 *
 * Deliberately vanilla JS with no build step and no external dependency --
 * this is served directly by the integration's own static path, so it
 * needs to work as-is in the browser with no bundler.
 *
 * PINs are never read from or written to hass.states: they only ever
 * travel as the immediate payload of a set_pin/verify_pin service call,
 * so they never enter Home Assistant's state machine, recorder, or
 * logbook history. Status (has_pin / locked_out) is fetched explicitly
 * via the list_pin_status service, not derived from entity state.
 */
class ExtendedUserManagementCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this._status = {};
    this._phoneNumbers = {};
    this._rowErrors = {};
    this._render();
  }

  set hass(hass) {
    // Home Assistant calls this setter on *every* state change anywhere
    // in the house, not just ones this card cares about. Only trigger
    // work on the first assignment -- a full re-render on every tick
    // would wipe out a PIN the admin is mid-way through typing.
    const firstRun = !this._hass;
    this._hass = hass;
    if (firstRun) {
      this._refresh();
    }
  }

  getCardSize() {
    return 3;
  }

  static _escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  _personName(entityId) {
    const state = this._hass && this._hass.states[entityId];
    const name = (state && state.attributes && state.attributes.friendly_name) || entityId;
    return ExtendedUserManagementCard._escapeHtml(name);
  }

  async _refresh() {
    if (!this._hass) {
      return;
    }
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: "extended_user_management",
        service: "list_pin_status",
        service_data: {},
        return_response: true,
      });
      this._status = (result && result.response && result.response.profiles) || {};
      this._loadError = null;
    } catch (err) {
      this._loadError = "Could not load PIN status. Is the integration set up?";
      this._render();
      return;
    }
    await this._refreshPhoneNumbers();
    this._render();
  }

  async _refreshPhoneNumbers() {
    // phone_number is a plain profile value (not a secret like the PIN), so
    // unlike list_pin_status this needs one get_profile_value call per
    // person -- there is no batch "list all profile values" service.
    const entries = await Promise.all(
      Object.keys(this._status).map(async (entityId) => {
        try {
          const result = await this._hass.callWS({
            type: "call_service",
            domain: "extended_user_management",
            service: "get_profile_value",
            service_data: { person_entity_id: entityId, key: "phone_number" },
            return_response: true,
          });
          const value = result && result.response && result.response.value;
          return [entityId, typeof value === "string" ? value : ""];
        } catch (err) {
          return [entityId, ""];
        }
      })
    );
    this._phoneNumbers = Object.fromEntries(entries);
  }

  async _setPin(entityId, pin) {
    if (!/^[0-9]{4,8}$/.test(pin)) {
      this._rowErrors[entityId] = "PIN must be 4-8 digits.";
      this._render();
      return;
    }
    try {
      await this._hass.callService("extended_user_management", "set_pin", {
        person_entity_id: entityId,
        pin,
      });
      delete this._rowErrors[entityId];
      await this._refresh();
    } catch (err) {
      this._rowErrors[entityId] = "Could not set PIN.";
      this._render();
    }
  }

  async _clearPin(entityId) {
    try {
      await this._hass.callService("extended_user_management", "clear_pin", {
        person_entity_id: entityId,
      });
      delete this._rowErrors[entityId];
      await this._refresh();
    } catch (err) {
      this._rowErrors[entityId] = "Could not clear PIN.";
      this._render();
    }
  }

  async _setPhoneNumber(entityId, phoneNumber) {
    const trimmed = phoneNumber.trim();
    // Blank is allowed -- it clears the number (there is no separate
    // clear_profile_value service). Anything non-blank is held to a loose
    // E.164 shape, since find_person_by_phone only ever does an exact
    // string match against whatever a caller ID actually looks like.
    if (trimmed && !/^\+[1-9][0-9]{6,14}$/.test(trimmed)) {
      this._rowErrors[entityId] = "Phone number must be E.164, e.g. +15551234567.";
      this._render();
      return;
    }
    try {
      await this._hass.callService("extended_user_management", "set_profile_value", {
        person_entity_id: entityId,
        key: "phone_number",
        value: trimmed,
      });
      delete this._rowErrors[entityId];
      this._phoneNumbers[entityId] = trimmed;
      this._render();
    } catch (err) {
      this._rowErrors[entityId] = "Could not save phone number.";
      this._render();
    }
  }

  _rowHtml(entityId) {
    const status = this._status[entityId] || {};
    const error = this._rowErrors[entityId];
    const statusLabel = status.locked_out ? "Locked out" : status.has_pin ? "PIN set" : "No PIN";
    const phoneNumber = this._phoneNumbers[entityId] || "";
    return `
      <div class="person" data-entity="${ExtendedUserManagementCard._escapeHtml(entityId)}">
        <div class="row">
          <span class="name">${this._personName(entityId)}</span>
          <span class="status${status.locked_out ? " locked" : ""}">${statusLabel}</span>
          <input type="password" inputmode="numeric" maxlength="8" placeholder="New PIN" class="pin-input" autocomplete="off" />
          <button class="set-btn">Set</button>
          <button class="clear-btn"${status.has_pin ? "" : " disabled"}>Clear</button>
        </div>
        <div class="row">
          <span class="name phone-label">Phone number</span>
          <input type="tel" placeholder="+15551234567" class="phone-input" autocomplete="off" value="${ExtendedUserManagementCard._escapeHtml(phoneNumber)}" />
          <button class="phone-save-btn">Save</button>
        </div>
        ${error ? `<div class="error">${ExtendedUserManagementCard._escapeHtml(error)}</div>` : ""}
      </div>
    `;
  }

  _render() {
    const root = this.shadowRoot;
    const people = Object.keys(this._status).sort((a, b) =>
      this._personName(a).localeCompare(this._personName(b))
    );
    root.innerHTML = `
      <style>
        ha-card { padding: 16px; }
        .content p { color: var(--secondary-text-color); }
        .person { padding: 8px 0; border-bottom: 1px solid var(--divider-color); }
        .person:last-child { border-bottom: none; }
        .row { display: flex; align-items: center; gap: 8px; padding: 4px 0; flex-wrap: wrap; }
        .name { flex: 1; font-weight: 500; min-width: 100px; }
        .name.phone-label { font-weight: 400; color: var(--secondary-text-color); }
        .status { font-size: 0.85em; color: var(--secondary-text-color); min-width: 80px; }
        .status.locked { color: var(--error-color); }
        input[type="password"], input[type="tel"] { width: 140px; padding: 6px; border: 1px solid var(--divider-color); border-radius: 4px; background: var(--card-background-color); color: var(--primary-text-color); }
        button { padding: 6px 12px; border: none; border-radius: 4px; background: var(--primary-color); color: var(--text-primary-color, #fff); cursor: pointer; }
        button:disabled { opacity: 0.4; cursor: default; }
        button.clear-btn { background: var(--error-color, #db4437); }
        .error { width: 100%; color: var(--error-color); font-size: 0.8em; padding: 0 0 8px; }
      </style>
      <ha-card header="Household PINs &amp; Phone Numbers">
        <div class="content">
          ${this._loadError ? `<p class="error">${ExtendedUserManagementCard._escapeHtml(this._loadError)}</p>` : ""}
          ${people.length === 0 && !this._loadError ? "<p>No person entities found.</p>" : ""}
          ${people.map((id) => this._rowHtml(id)).join("")}
        </div>
      </ha-card>
    `;
    people.forEach((id) => this._wireRow(id));
  }

  _wireRow(entityId) {
    const person = this.shadowRoot.querySelector(`.person[data-entity="${CSS.escape(entityId)}"]`);
    if (!person) {
      return;
    }
    const pinInput = person.querySelector(".pin-input");
    person.querySelector(".set-btn").addEventListener("click", () => {
      this._setPin(entityId, pinInput.value.trim());
    });
    person.querySelector(".clear-btn").addEventListener("click", () => {
      this._clearPin(entityId);
    });
    pinInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        this._setPin(entityId, pinInput.value.trim());
      }
    });

    const phoneInput = person.querySelector(".phone-input");
    person.querySelector(".phone-save-btn").addEventListener("click", () => {
      this._setPhoneNumber(entityId, phoneInput.value);
    });
    phoneInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        this._setPhoneNumber(entityId, phoneInput.value);
      }
    });
  }
}

customElements.define("extended-user-management-card", ExtendedUserManagementCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "extended-user-management-card",
  name: "Extended User Management",
  description: "Manage per-person PINs and phone numbers for HA Extended User Management.",
});
