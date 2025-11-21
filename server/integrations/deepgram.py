"""
PHRONAI Deepgram Integration

Async client for Deepgram Speech-to-Text API.
Ported from Kotlin's DeepgramClient.kt with Python async patterns.
"""

import logging
from typing import Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# Deepgram API configuration
DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_MODEL = "nova-2"


class DeepgramError(Exception):
    """Custom exception for Deepgram API errors."""
    pass


class DeepgramClient:
    """
    Async client for Deepgram Speech-to-Text.
    
    Uses the pre-recorded API for audio transcription.
    Optimized for WebM/Opus audio from browser MediaRecorder.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.DEEPGRAM_API_KEY
        if not self.api_key:
            logger.warning("DEEPGRAM_API_KEY not set - transcription will fail")
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=10.0),
                limits=httpx.Limits(max_connections=10),
            )
        return self._client
    
    async def transcribe(self, audio_data: bytes) -> str:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes (WebM/Opus format expected)
        
        Returns:
            Transcribed text
        
        Raises:
            DeepgramError: If transcription fails
        """
        if not self.api_key:
            raise DeepgramError("DEEPGRAM_API_KEY not configured")
        
        if len(audio_data) < 100:
            raise DeepgramError("Audio data too small (minimum 100 bytes)")
        
        if len(audio_data) > 10 * 1024 * 1024:
            raise DeepgramError("Audio data too large (maximum 10MB)")
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                DEEPGRAM_API_URL,
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "audio/webm",
                },
                params={
                    "model": DEEPGRAM_MODEL,
                    "smart_format": "true",
                    "punctuate": "true",
                },
                content=audio_data,
            )
            
            if response.status_code != 200:
                error_text = response.text[:200]
                logger.error(f"Deepgram API error {response.status_code}: {error_text}")
                raise DeepgramError(f"Deepgram API returned {response.status_code}")
            
            data = response.json()
            
            # Extract transcript from response
            results = data.get("results", {})
            channels = results.get("channels", [])
            
            if not channels:
                logger.warning("No channels in Deepgram response")
                return ""
            
            alternatives = channels[0].get("alternatives", [])
            if not alternatives:
                logger.warning("No alternatives in Deepgram response")
                return ""
            
            transcript = alternatives[0].get("transcript", "")
            
            logger.info(f"Transcribed {len(audio_data)} bytes -> '{transcript[:50]}...'")
            return transcript.strip()
        
        except httpx.TimeoutException:
            logger.error("Deepgram API timeout")
            raise DeepgramError("Transcription timed out")
        
        except httpx.RequestError as e:
            logger.error(f"Deepgram API request error: {e}")
            raise DeepgramError(f"Request failed: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error in transcription: {e}")
            raise DeepgramError(f"Transcription failed: {e}")
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# Global client instance
deepgram_client = DeepgramClient()
