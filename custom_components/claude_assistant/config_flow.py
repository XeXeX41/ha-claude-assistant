"""Config flow for Claude Assistant integration."""
from __future__ import annotations
import logging
from homeassistant import config_entries
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

DOMAIN = "claude_assistant"
CONF_API_KEY = "api_key"

class ClaudeAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Claude Assistant."""
    
    VERSION = 1
    
    async def async_step_user(self, user_input=None):
        """Handle user step."""
        errors = {}
        
        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            
            # Simple validation - just check format
            if not api_key.startswith("sk-ant-"):
                errors["base"] = "invalid_api_key"
            else:
                # Key looks valid, accept it
                return self.async_create_entry(
                    title="Claude AI Assistant",
                    data=user_input,
                )
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
            }),
            errors=errors,
            description_placeholders={
                "api_key_url": "https://console.anthropic.com/"
            },
        )