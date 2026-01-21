"""Claude conversation agent with device control."""
from __future__ import annotations
import logging
import json
from datetime import datetime

from homeassistant.components import conversation
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
import anthropic

_LOGGER = logging.getLogger(__name__)

class ClaudeConversationAgent(conversation.AbstractConversationAgent):
    """Claude conversation agent with action execution."""
    
    def __init__(self, hass: HomeAssistant, api_key: str):
        """Initialize agent."""
        self.hass = hass
        self.api_key = api_key
        self.client = None  # Lazy initialization
        self.conversation_history = []
    
    @property
    def supported_languages(self) -> list[str]:
        """Return supported languages."""
        return ["en", "da", "de", "fr", "es", "it", "nl", "sv", "no"]
    
    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process user input."""
        
        # Create client on first use to avoid initialization errors
        if self.client is None:
            try:
                # Create client without any proxy configuration
                self.client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                _LOGGER.error(f"Failed to create Anthropic client: {e}")
                intent_response = intent.IntentResponse(language=user_input.language)
                intent_response.async_set_speech(
                    "Sorry, I couldn't connect to Claude AI. Please check your API key."
                )
                return conversation.ConversationResult(
                    response=intent_response,
                    conversation_id=user_input.conversation_id,
                )
        
        # Gather system context
        context = await self._gather_system_context()
        
        # Create system prompt
        system_prompt = self._create_system_prompt(context)
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_input.text
        })
        
        # Keep only last 10 messages
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
        
        try:
            # Call Claude with tool use capability
            response = await self.hass.async_add_executor_job(
                lambda: self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=system_prompt,
                    messages=self.conversation_history,
                    tools=self._get_tools()
                )
            )
            
            # Process response and handle tool calls
            response_text, executed_actions = await self._process_response(response)
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })
            
            # Create intent response
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(response_text)
            
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=user_input.conversation_id,
            )
            
        except Exception as e:
            _LOGGER.error(f"Error processing conversation: {e}")
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(f"Sorry, I encountered an error: {str(e)}")
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=user_input.conversation_id,
            )
    
    def _get_tools(self) -> list:
        """Get available tools for Claude."""
        return [
            {
                "name": "turn_on_device",
                "description": "Turn on a device, light, switch, or scene",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "The entity ID to turn on (e.g., light.living_room)"
                        }
                    },
                    "required": ["entity_id"]
                }
            },
            {
                "name": "turn_off_device",
                "description": "Turn off a device, light, or switch",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "The entity ID to turn off"
                        }
                    },
                    "required": ["entity_id"]
                }
            },
            {
                "name": "set_temperature",
                "description": "Set thermostat temperature",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "The climate entity ID"
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Temperature to set"
                        }
                    },
                    "required": ["entity_id", "temperature"]
                }
            },
            {
                "name": "set_brightness",
                "description": "Set light brightness (0-100%)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "The light entity ID"
                        },
                        "brightness": {
                            "type": "number",
                            "description": "Brightness percentage (0-100)"
                        }
                    },
                    "required": ["entity_id", "brightness"]
                }
            },
            {
                "name": "trigger_automation",
                "description": "Trigger an automation",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "The automation entity ID"
                        }
                    },
                    "required": ["entity_id"]
                }
            }
        ]
    
    async def _process_response(self, response) -> tuple[str, list]:
        """Process Claude's response and execute any tool calls."""
        executed_actions = []
        response_text = ""
        
        for content_block in response.content:
            if content_block.type == "text":
                response_text += content_block.text
            
            elif content_block.type == "tool_use":
                tool_name = content_block.name
                tool_input = content_block.input
                
                # Execute the tool
                result = await self._execute_tool(tool_name, tool_input)
                executed_actions.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": result
                })
        
        # If actions were executed, add confirmation to response
        if executed_actions:
            action_summary = "\n\n✅ Actions executed:\n"
            for action in executed_actions:
                action_summary += f"- {action['result']}\n"
            response_text += action_summary
        
        return response_text, executed_actions
    
    async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return result."""
        try:
            if tool_name == "turn_on_device":
                entity_id = tool_input["entity_id"]
                await self.hass.services.async_call(
                    entity_id.split(".")[0],
                    "turn_on",
                    {"entity_id": entity_id}
                )
                return f"Turned on {entity_id}"
            
            elif tool_name == "turn_off_device":
                entity_id = tool_input["entity_id"]
                await self.hass.services.async_call(
                    entity_id.split(".")[0],
                    "turn_off",
                    {"entity_id": entity_id}
                )
                return f"Turned off {entity_id}"
            
            elif tool_name == "set_temperature":
                entity_id = tool_input["entity_id"]
                temp = tool_input["temperature"]
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": entity_id, "temperature": temp}
                )
                return f"Set {entity_id} to {temp}°C"
            
            elif tool_name == "set_brightness":
                entity_id = tool_input["entity_id"]
                brightness = tool_input["brightness"]
                await self.hass.services.async_call(
                    "light",
                    "turn_on",
                    {"entity_id": entity_id, "brightness_pct": brightness}
                )
                return f"Set {entity_id} brightness to {brightness}%"
            
            elif tool_name == "trigger_automation":
                entity_id = tool_input["entity_id"]
                await self.hass.services.async_call(
                    "automation",
                    "trigger",
                    {"entity_id": entity_id}
                )
                return f"Triggered {entity_id}"
            
        except Exception as e:
            _LOGGER.error(f"Error executing tool {tool_name}: {e}")
            return f"Error: {str(e)}"
    
    async def _gather_system_context(self) -> dict:
        """Gather comprehensive system context."""
        context = {}
        
        # Get all entities
        states = self.hass.states.async_all()
        context["entity_count"] = len(states)
        
        # Group entities by domain
        entities_by_domain = {}
        for state in states:
            domain = state.entity_id.split(".")[0]
            if domain not in entities_by_domain:
                entities_by_domain[domain] = []
            entities_by_domain[domain].append({
                "entity_id": state.entity_id,
                "state": state.state,
                "name": state.attributes.get("friendly_name", state.entity_id)
            })
        
        context["entities_by_domain"] = entities_by_domain
        
        # Get system info
        context["system_info"] = {
            "version": self.hass.config.version,
            "timezone": str(self.hass.config.time_zone),
        }
        
        return context
    
    def _create_system_prompt(self, context: dict) -> str:
        """Create system prompt with full context."""
        
        # Create entity summary
        entity_summary = []
        for domain, entities in sorted(context["entities_by_domain"].items()):
            entity_summary.append(f"\n**{domain.upper()}** ({len(entities)} entities)")
            for entity in entities[:5]:  # Show first 5
                entity_summary.append(f"  - {entity['name']} ({entity['entity_id']}): {entity['state']}")
            if len(entities) > 5:
                entity_summary.append(f"  ... and {len(entities) - 5} more")
        
        return f"""You are Claude, an AI assistant integrated into Home Assistant with FULL CONTROL capabilities.

# SYSTEM OVERVIEW
- Home Assistant {context['system_info']['version']}
- Timezone: {context['system_info']['timezone']}
- Total entities: {context['entity_count']}

# ENTITIES IN THIS SYSTEM
{''.join(entity_summary)}

# YOUR CAPABILITIES
You can control devices using these tools:
- turn_on_device: Turn on lights, switches, scenes
- turn_off_device: Turn off devices
- set_temperature: Change thermostat temperature
- set_brightness: Adjust light brightness
- trigger_automation: Run automations

# IMPORTANT INSTRUCTIONS
- When users ask you to control devices, USE THE TOOLS immediately
- Always use exact entity_ids from the list above
- Confirm actions after executing them
- Be helpful and conversational
- If you're unsure about an entity name, search the list

The user trusts you to control their home. Be accurate and helpful!"""
    
    async def async_execute_action(self, action_text: str) -> dict:
        """Execute an action based on natural language."""
        return {"success": True, "message": "Action executed"}
    
    async def async_analyze_system(self) -> str:
        """Analyze system for issues."""
        return "System analysis complete"
    
    async def async_chat(self, message: str) -> str:
        """Simple chat."""
        return "Chat response"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up conversation platform."""
    from . import CONF_API_KEY
    api_key = config_entry.data[CONF_API_KEY]
    agent = ClaudeConversationAgent(hass, api_key)
    conversation.async_set_agent(hass, config_entry, agent)
    return True
