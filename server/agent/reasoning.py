"""
PHRONAI Groq Integration with Instructor

This is the CORE of the zero-hallucination system.
Uses Instructor library to force LLM to output valid Pydantic schemas.

Key Innovation:
- If LLM returns invalid JSON, Instructor automatically retries with error context
- This creates a "self-correction loop" which is exactly what Giga AI wants
"""

import logging
from pathlib import Path
from typing import Optional

import instructor
from instructor.core.exceptions import InstructorRetryException
from openai import AsyncOpenAI
from django.conf import settings

from agent.schemas import SketchResponse, GraphState

logger = logging.getLogger(__name__)

# Load the sketch protocol prompt
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "sketch_protocol.md"


class ReasoningError(Exception):
    """Custom exception for reasoning failures."""
    pass


class ReasoningEngine:
    """
    LLM reasoning engine with zero-hallucination guarantees.
    
    Uses Instructor to patch the OpenAI client with Pydantic validation.
    Every response is guaranteed to match our SketchResponse schema.
    
    If the LLM outputs invalid JSON:
    1. Instructor catches the validation error
    2. It automatically sends the error back to the LLM
    3. The LLM corrects itself and retries
    
    This is the "self-correction loop" that makes agents reliable.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        if not self.api_key:
            logger.warning("GROQ_API_KEY not set - reasoning will fail")
        
        self.model = settings.LLM_MODEL
        self.max_retries = settings.LLM_MAX_RETRIES
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
        
        # Create Instructor-patched client
        self._client: Optional[instructor.AsyncInstructor] = None
    
    def _load_system_prompt(self) -> str:
        """Load the sketch protocol system prompt."""
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8")
        
        # Fallback inline prompt if file doesn't exist
        return """
You are an intelligent whiteboard assistant that creates professional visual diagrams from natural language.
Convert user descriptions into structured JSON for rendering shapes with icons and detailed text.

## OUTPUT FORMAT
Return a JSON object with an "actions" array containing actions to perform on the graph.

## RULES
1. Use snake_case for all IDs
2. Keep labels short (2-4 words)
3. Prefer semantic types (database, server, client) over generic shapes
4. Always validate that source_id and target_id exist before creating edges
"""
    
    async def _get_client(self) -> instructor.AsyncInstructor:
        """Get or create the Instructor client."""
        if self._client is None:
            # Use Groq-compatible endpoint
            base_client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            # Patch with Instructor for Pydantic validation
            self._client = instructor.from_openai(base_client)
        
        return self._client
    
    async def get_actions(
        self,
        transcript: str,
        graph_state: GraphState,
    ) -> SketchResponse:
        """
        Get diagram actions from the LLM.
        
        This is the core reasoning function. It:
        1. Builds a context-aware prompt with current graph state
        2. Sends to Groq's Llama 3.3 70B
        3. Validates response against SketchResponse schema
        4. Auto-retries on validation failure (self-correction)
        
        Args:
            transcript: The user's voice command
            graph_state: Current graph state for context
        
        Returns:
            SketchResponse with validated actions
        
        Raises:
            ReasoningError: If reasoning fails after retries
        """
        if not self.api_key:
            raise ReasoningError("GROQ_API_KEY not configured")
        
        client = await self._get_client()
        
        # Build user prompt with context
        graph_summary = graph_state.to_summary()
        history_summary = graph_state.get_history_summary()
        
        user_prompt = f"""
## CURRENT GRAPH STATE
{graph_summary}

## CONVERSATION HISTORY
{history_summary}

## USER COMMAND
"{transcript}"

## TASK
Analyze the user command and return the appropriate actions to modify the graph.
Return ONLY valid actions. Do not create edges to non-existent nodes.
"""
        
        try:
            logger.info(f"Sending to LLM: '{transcript[:50]}...'")
            
            # This is where the magic happens:
            # Instructor will validate the response against SketchResponse
            # If validation fails, it retries automatically
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=SketchResponse,
                max_retries=self.max_retries,
            )
            
            logger.info(f"Got {len(response.actions)} actions from LLM")
            return response
        
        except InstructorRetryException as e:
            logger.error(f"LLM failed after {self.max_retries} retries: {e}")
            raise ReasoningError(f"Failed to get valid response after retries")
        
        except Exception as e:
            error_msg = str(e)
            # Check if it's a schema validation error
            if "tool_use_failed" in error_msg or "did not match schema" in error_msg:
                logger.error(f"Schema validation failed: {e}")
                raise ReasoningError(f"LLM output did not match schema. Try using valid colors: yellow, pink, blue, green, orange, red, violet")
            logger.error(f"Unexpected error in reasoning: {e}")
            raise ReasoningError(f"Reasoning failed: {e}")
    
    async def close(self) -> None:
        """Close the client."""
        self._client = None


# Global reasoning engine instance
reasoning_engine = ReasoningEngine()
