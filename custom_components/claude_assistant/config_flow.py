"""Config flow for Claude Assistant integration."""
from __future__ import annotations
import logging
from homeassistant import config_entries
import voluptuous as vol
import anthropic

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
            
            # Validate API key
            try:
                client = anthropic.Anthropic(api_key=api_key)
                await self.hass.async_add_executor_job(
                    lambda: client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=10,
                        messages=[{"role": "user", "content": "test"}]
                    )
                )
                
                return self.async_create_entry(
                    title="Claude AI Assistant",
                    data=user_input,
                )
            except Exception as e:
                _LOGGER.error(f"API key validation failed: {e}")
                errors["base"] = "invalid_api_key"
        
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