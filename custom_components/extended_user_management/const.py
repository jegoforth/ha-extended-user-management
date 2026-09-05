"""Constants for the HA Extended User Management integration."""

DOMAIN = "extended_user_management"
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.profiles"

SERVICE_SET_PIN = "set_pin"
SERVICE_VERIFY_PIN = "verify_pin"
SERVICE_CLEAR_PIN = "clear_pin"
SERVICE_SET_PROFILE_VALUE = "set_profile_value"
SERVICE_GET_PROFILE_VALUE = "get_profile_value"

ATTR_PERSON_ENTITY_ID = "person_entity_id"
ATTR_PIN = "pin"
ATTR_KEY = "key"
ATTR_VALUE = "value"
ATTR_VERIFIED = "verified"
ATTR_LOCKED_OUT = "locked_out"

MIN_PIN_LENGTH = 4
MAX_PIN_LENGTH = 8
MAX_PIN_ATTEMPTS = 3
LOCKOUT_SECONDS = 300
PBKDF2_ITERATIONS = 200_000
