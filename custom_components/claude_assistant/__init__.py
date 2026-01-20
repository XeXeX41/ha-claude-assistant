"""
Home Assistant Claude AI Integration
Provides Claude with full context of your HA system for better assistance
"""

from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

DOMAIN = "claude_assistant"
CONF_API_KEY = "api_key"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema({
            vol.Required(CONF_API_KEY): cv.string,
        })
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up Claude Assistant component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Claude Assistant from config entry."""
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(
        entry, ["conversation"]
    )
    
    # Register services
    await async_setup_services(hass, entry)
    
    return True

async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry):
    """Register services."""
    from .conversation import ClaudeConversationAgent
    
    api_key = entry.data[CONF_API_KEY]
    agent = ClaudeConversationAgent(hass, api_key)
    
    async def handle_execute_action(call: ServiceCall):
        """Handle execute_action service call."""
        action_text = call.data.get("action")
        result = await agent.async_execute_action(action_text)
        return {"success": result["success"], "message": result["message"]}
    
    async def handle_analyze_system(call: ServiceCall):
        """Analyze system for issues."""
        analysis = await agent.async_analyze_system()
        return {"analysis": analysis}
    
    async def handle_chat(call: ServiceCall):
        """Chat with Claude."""
        message = call.data.get("message")
        response = await agent.async_chat(message)
        return {"response": response}
    
    hass.services.async_register(
        DOMAIN,
        "execute_action",
        handle_execute_action,
        schema=vol.Schema({
            vol.Required("action"): cv.string,
        }),
    )
    
    hass.services.async_register(
        DOMAIN,
        "analyze_system",
        handle_analyze_system,
    )
    
    hass.services.async_register(
        DOMAIN,
        "chat",
        handle_chat,
        schema=vol.Schema({
            vol.Required("message"): cv.string,
        }),
    )

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["conversation"]
    )
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.services.async_remove(DOMAIN, "execute_action")
        hass.services.async_remove(DOMAIN, "analyze_system")
        hass.services.async_remove(DOMAIN, "chat")
    
    return unload_ok