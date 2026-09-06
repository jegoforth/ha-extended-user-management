"""Constants for the HA Extended User Management integration."""

DOMAIN = "extended_user_management"
STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.profiles"

SERVICE_SET_PIN = "set_pin"
SERVICE_VERIFY_PIN = "verify_pin"
SERVICE_CLEAR_PIN = "clear_pin"
SERVICE_SET_PROFILE_VALUE = "set_profile_value"
SERVICE_GET_PROFILE_VALUE = "get_profile_value"
SERVICE_LIST_PIN_STATUS = "list_pin_status"
SERVICE_FIND_PERSON_BY_PHONE = "find_person_by_phone"

ATTR_PERSON_ENTITY_ID = "person_entity_id"
ATTR_PIN = "pin"
ATTR_KEY = "key"
ATTR_VALUE = "value"
ATTR_VERIFIED = "verified"
ATTR_LOCKED_OUT = "locked_out"
ATTR_HAS_PIN = "has_pin"
ATTR_PROFILES = "profiles"
ATTR_NAME = "name"
ATTR_PHONE_NUMBER = "phone_number"

# Well-known profile key backing find_person_by_phone's reverse lookup.
# Set it like any other profile value (extended_user_management.set_profile_value,
# key: phone_number) -- there is nothing phone-specific about how it is stored.
PROFILE_KEY_PHONE_NUMBER = "phone_number"

MIN_PIN_LENGTH = 4
MAX_PIN_LENGTH = 8
MAX_PIN_ATTEMPTS = 3
LOCKOUT_SECONDS = 300
PBKDF2_ITERATIONS = 200_000
