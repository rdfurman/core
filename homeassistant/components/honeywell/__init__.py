"""Support for Honeywell (US) Total Connect Comfort climate systems."""

from somecomfort import AuthError, SomeComfort, SomeComfortError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    _LOGGER,
    CONF_COOL_AWAY_TEMPERATURE,
    CONF_HEAT_AWAY_TEMPERATURE,
    DOMAIN,
)

UPDATE_LOOP_SLEEP_TIME = 5
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

MIGRATE_OPTIONS_KEYS = {CONF_COOL_AWAY_TEMPERATURE, CONF_HEAT_AWAY_TEMPERATURE}


@callback
def _async_migrate_data_to_options(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> None:
    if not MIGRATE_OPTIONS_KEYS.intersection(config_entry.data):
        return
    hass.config_entries.async_update_entry(
        config_entry,
        data={
            k: v for k, v in config_entry.data.items() if k not in MIGRATE_OPTIONS_KEYS
        },
        options={
            **config_entry.options,
            **{k: config_entry.data.get(k) for k in MIGRATE_OPTIONS_KEYS},
        },
    )


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up the Honeywell thermostat."""
    _async_migrate_data_to_options(hass, config_entry)

    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    honeywell_api = await hass.async_add_executor_job(
        get_somecomfort_client, username, password
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = honeywell_api

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    return True


def get_somecomfort_client(username: str, password: str) -> SomeComfort:
    """Initialize the somecomfort client."""
    try:
        return SomeComfort(username, password)
    except AuthError:
        _LOGGER.error("Failed to login to honeywell account %s", username)
        return None
    except SomeComfortError as ex:
        raise ConfigEntryNotReady(
            "Failed to initialize the Honeywell client: "
            "Check your configuration (username, password), "
            "or maybe you have exceeded the API rate limit?"
        ) from ex


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload the config config and platforms."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        hass.data.pop(DOMAIN)
    return unload_ok
