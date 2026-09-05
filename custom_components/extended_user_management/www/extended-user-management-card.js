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
    }
    this._render();
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

  _rowHtml(entityId) {
    const status = this._status[entityId] || {};
    const error = this._rowErrors[entityId];
    const statusLabel = status.locked_out ? "Locked out" : status.has_pin ? "PIN set" : "No PIN";
    return `
      <div class="row" data-entity="${ExtendedUserManagementCard._escapeHtml(entityId)}">
        <span class="name">${this._personName(entityId)}</span>
        <span class="status${status.locked_out ? " locked" : ""}">${statusLabel}</span>
        <input type="password" inputmode="numeric" maxlength="8" placeholder="New PIN" class="pin-input" autocomplete="off" />
        <button class="set-btn">Set</button>
        <button class="clear-btn"${status.has_pin ? "" : " disabled"}>Clear</button>
      </div>
      ${error ? `<div class="error">${ExtendedUserManagementCard._escapeHtml(error)}</div>` : ""}
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
        .row { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--divider-color); flex-wrap: wrap; }
        .row:last-child { border-bottom: none; }
        .name { flex: 1; font-weight: 500; min-width: 100px; }
        .status { font-size: 0.85em; color: var(--secondary-text-color); min-width: 80px; }
        .status.locked { color: var(--error-color); }
        input[type="password"] { width: 100px; padding: 6px; border: 1px solid var(--divider-color); border-radius: 4px; background: var(--card-background-color); color: var(--primary-text-color); }
        button { padding: 6px 12px; border: none; border-radius: 4px; background: var(--primary-color); color: var(--text-primary-color, #fff); cursor: pointer; }
        button:disabled { opacity: 0.4; cursor: default; }
        button.clear-btn { background: var(--error-color, #db4437); }
        .error { width: 100%; color: var(--error-color); font-size: 0.8em; padding: 0 0 8px; }
      </style>
      <ha-card header="Household PINs">
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
    const row = this.shadowRoot.querySelector(`.row[data-entity="${CSS.escape(entityId)}"]`);
    if (!row) {
      return;
    }
    const input = row.querySelector(".pin-input");
    row.querySelector(".set-btn").addEventListener("click", () => {
      this._setPin(entityId, input.value.trim());
    });
    row.querySelector(".clear-btn").addEventListener("click", () => {
      this._clearPin(entityId);
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        this._setPin(entityId, input.value.trim());
      }
    });
  }
}

customElements.define("extended-user-management-card", ExtendedUserManagementCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "extended-user-management-card",
  name: "Extended User Management",
  description: "Manage per-person PINs for HA Extended User Management.",
});
