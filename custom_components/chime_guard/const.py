"""Constants for the Chime Guard integration."""

DOMAIN = "chime_guard"
VERSION = "1.0.0"

# Configuration & Options keys
CONF_SPEAKER_MAPPINGS = "speaker_mappings"  # Dict[str, str]: mass/custom entity_id -> physical cast_entity_id
CONF_MIN_MUTE_WINDOW = "min_mute_window"  # Integer milliseconds (e.g. 1800)
CONF_MAX_TIMEOUT = "max_timeout"  # Integer seconds (e.g. 12)
CONF_EXTERNAL_TAKEOVER = "external_takeover"  # Boolean
CONF_MUTE_METHOD = "mute_method"  # "volume_mute" or "volume_zero"
CONF_INTERCEPT_JOIN = "intercept_join"  # Boolean
CONF_EXCLUDED_SPEAKERS = "excluded_speakers"  # List[str]

# Defaults
DEFAULT_MIN_MUTE_WINDOW = 1800  # ms
DEFAULT_MAX_TIMEOUT = 12  # seconds
DEFAULT_EXTERNAL_TAKEOVER = True
DEFAULT_MUTE_METHOD = "volume_mute"
DEFAULT_INTERCEPT_JOIN = True

# Known Music Assistant receiver app names / IDs on Google Cast
KNOWN_MA_APPS = [
    "sendspin",
    "music assistant",
    "mass",
    "dd107ddb",
]

# Static path for frontend distribution
URL_BASE = "/chime_guard_static"
FRONTEND_SCRIPT_FILENAME = "chime_guard.js"
FRONTEND_SCRIPT_URL = f"{URL_BASE}/{FRONTEND_SCRIPT_FILENAME}"

# WebSocket API
WS_TYPE_GET_CONFIG = f"{DOMAIN}/config"
