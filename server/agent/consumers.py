"""
PHRONAI WebSocket Consumer

The main entry point for voice-to-action processing.
Ported from Kotlin's Application.kt WebSocket handler.

This is the orchestration layer that coordinates:
1. Audio → Transcription (Deepgram)
2. Transcription → Reasoning (Groq + Instructor)
3. Actions → State Updates
4. State → Client Sync
"""

import json
import logging
import time
from typing import Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .schemas import CanvasSyncMessage, SketchResponse
from .state import state_manager
from .reasoning import reasoning_engine, ReasoningError
from integrations.deepgram import deepgram_client, DeepgramError

logger = logging.getLogger(__name__)


class AgentConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for the PHRONAI agent.
    
    Handles:
    - Binary frames: Audio data for transcription
    - Text frames: Canvas sync messages from client
    
    This is the Python equivalent of Kotlin's webSocket("/ws") handler.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id: Optional[str] = None
        self.connection_time: float = 0
    
    async def connect(self) -> None:
        """Handle WebSocket connection."""
        # Extract token from query params
        query_string = self.scope.get("query_string", b"").decode()
        params = dict(p.split("=") for p in query_string.split("&") if "=" in p)
        
        token = params.get("token")
        if not token:
            logger.warning("Connection attempt without token")
            await self.close(code=4001)
            return
        
        # TODO: Verify JWT token with Supabase
        # For now, use token as user_id (in production, decode JWT)
        self.user_id = self._extract_user_id(token)
        
        if not self.user_id:
            logger.warning("Invalid token")
            await self.close(code=4001)
            return
        
        await self.accept()
        self.connection_time = time.time()
        
        logger.info(f"User {self.user_id} connected")
        
        # Initialize or load session
        session = await state_manager.get_or_create(self.user_id)
        
        # Send welcome message
        await self.send_json({
            "type": "connected",
            "message": "Connected to PHRONAI",
            "version": "1.0.0",
        })
        
        # Load and send saved state if exists
        if session.canvas_snapshot:
            await self.send(text_data=session.canvas_snapshot)
            logger.info(f"Sent saved canvas to user {self.user_id}")
    
    async def disconnect(self, close_code: int) -> None:
        """Handle WebSocket disconnection."""
        if self.user_id:
            duration = time.time() - self.connection_time
            logger.info(f"User {self.user_id} disconnected after {duration:.1f}s")
            await state_manager.remove(self.user_id)
    
    async def receive(self, text_data: Optional[str] = None, bytes_data: Optional[bytes] = None) -> None:
        """Handle incoming messages."""
        if bytes_data:
            await self._handle_audio(bytes_data)
        elif text_data:
            await self._handle_text(text_data)
    
    async def _handle_audio(self, audio_data: bytes) -> None:
        """
        Process audio data.
        
        Flow:
        1. Validate audio
        2. Transcribe with Deepgram
        3. Get actions from reasoning engine
        4. Apply actions to state
        5. Send response to client
        """
        if not self.user_id:
            return
        
        logger.info(f"Received audio: {len(audio_data)} bytes")
        start_time = time.time()
        
        try:
            # Step 1: Transcribe
            transcript = await deepgram_client.transcribe(audio_data)
            
            if not transcript:
                await self.send_json({
                    "type": "error",
                    "message": "No speech detected - please speak clearly",
                })
                return
            
            # Send transcript to client immediately
            await self.send_json({
                "type": "transcript",
                "text": transcript,
            })
            
            logger.info(f"Transcript: '{transcript}'")
            
            # Step 2: Get current state
            session = await state_manager.get(self.user_id)
            if not session:
                logger.error(f"No session for user {self.user_id}")
                return
            
            # Step 3: Get actions from reasoning engine
            response = await reasoning_engine.get_actions(
                transcript=transcript,
                graph_state=session.graph,
            )
            
            logger.info(f"Got {len(response.actions)} actions")
            
            # Step 4: Apply actions
            for action in response.actions:
                success = await state_manager.apply_action(self.user_id, action)
                if success:
                    logger.debug(f"Applied action: {action.action.value} - {action.id}")
                else:
                    logger.warning(f"Failed to apply action: {action}")
            
            # Add to conversation history
            await state_manager.add_to_history(self.user_id, transcript)
            
            # Step 5: Send response to client
            await self.send_json({
                "type": "actions",
                "actions": [a.model_dump() for a in response.actions],
            })
            
            processing_time = time.time() - start_time
            logger.info(f"Processed in {processing_time:.2f}s")
        
        except DeepgramError as e:
            logger.error(f"Transcription error: {e}")
            await self.send_json({
                "type": "error",
                "message": f"Transcription failed: {e}",
            })
        
        except ReasoningError as e:
            logger.error(f"Reasoning error: {e}")
            await self.send_json({
                "type": "error",
                "message": f"Failed to generate diagram: {e}",
            })
        
        except Exception as e:
            logger.exception(f"Unexpected error processing audio: {e}")
            await self.send_json({
                "type": "error",
                "message": "An unexpected error occurred",
            })
    
    async def _handle_text(self, text_data: str) -> None:
        """Handle text messages (canvas sync, feedback, etc.)."""
        if not self.user_id:
            return
        
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")
            
            if msg_type == "canvas_sync":
                await self._handle_canvas_sync(data)
            elif msg_type == "feedback":
                await self._handle_feedback(data)
            else:
                logger.debug(f"Unknown message type: {msg_type}")
        
        except json.JSONDecodeError:
            logger.warning("Received invalid JSON")
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
    
    async def _handle_canvas_sync(self, data: dict) -> None:
        """Handle canvas sync from client."""
        if not self.user_id:
            return
        
        try:
            sync_msg = CanvasSyncMessage(**data)
            
            session = await state_manager.get(self.user_id)
            if session:
                session.canvas_snapshot = sync_msg.snapshot
                # Update graph state from client
                session.graph = sync_msg.graph
                logger.debug(f"Canvas synced: {len(sync_msg.graph.nodes)} nodes")
        
        except Exception as e:
            logger.error(f"Error processing canvas sync: {e}")
    
    async def _handle_feedback(self, data: dict) -> None:
        """
        Handle user feedback for self-learning.
        
        This is the "Self-Learning Agent" feature for Giga AI.
        Logs corrections to build a training dataset.
        """
        if not self.user_id:
            return
        
        # TODO: Log to training_data.jsonl for fine-tuning
        feedback_type = data.get("feedback_type")
        action_id = data.get("action_id")
        
        logger.info(f"User {self.user_id} feedback: {feedback_type} on {action_id}")
        
        # Acknowledge feedback
        await self.send_json({
            "type": "feedback_ack",
            "action_id": action_id,
            "status": "recorded",
        })
    
    def _extract_user_id(self, token: str) -> Optional[str]:
        """
        Extract user ID from token.
        
        TODO: Implement proper JWT verification with Supabase.
        For now, return a placeholder.
        """
        # In production, decode and verify the JWT
        # For development, just use a hash of the token
        if len(token) < 10:
            return None
        
        return f"user_{hash(token) % 100000}"
