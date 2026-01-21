"""Claude AI Assistant integration for Home Assistant."""
from __future__ import annotations
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.components import conversation as ha_conversation, frontend, websocket_api

_LOGGER = logging.getLogger(__name__)

DOMAIN = "claude_assistant"
CONF_API_KEY = "api_key"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Claude AI Assistant from a config entry."""
    
    # Store config
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Set up conversation platform
    from .conversation import ClaudeConversationAgent
    
    api_key = entry.data[CONF_API_KEY]
    agent = ClaudeConversationAgent(hass, api_key)
    ha_conversation.async_set_agent(hass, entry, agent)
    
    # Register the panel in the sidebar
    await async_register_panel(hass, entry)
    
    _LOGGER.info("Claude AI Assistant integration loaded successfully")
    
    return True


async def async_register_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register the Claude AI panel in the sidebar."""
    
    # Get paths
    integration_dir = Path(__file__).parent
    panel_source = integration_dir / "claude_assistant_panel.html"
    www_dir = Path(hass.config.path("www"))
    panel_dest = www_dir / "claude_assistant_panel.html"
    
    # Ensure www directory exists
    await hass.async_add_executor_job(www_dir.mkdir, parents=True, exist_ok=True)
    
    # Copy HTML file to www directory so HA can serve it
    if panel_source.exists():
        await hass.async_add_executor_job(
            lambda: panel_dest.write_text(panel_source.read_text(encoding='utf-8'), encoding='utf-8')
        )
        _LOGGER.info(f"Copied panel HTML to {panel_dest}")
    
    # Register panel as iframe pointing to www file
    frontend.async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title="Claude AI",
        sidebar_icon="mdi:robot",
        frontend_url_path="claude-assistant",
        config={"url": "/local/claude_assistant_panel.html"},
        require_admin=False,
    )
    
    _LOGGER.info("Claude AI Assistant panel registered in sidebar")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    # Remove from data
    hass.data[DOMAIN].pop(entry.entry_id)
    
    # Unload conversation
    ha_conversation.async_unset_agent(hass, entry)
    
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry."""
    # Clean up if needed
    pass
