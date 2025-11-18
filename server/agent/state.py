"""
PHRONAI State Manager

Manages the graph state for each user session.
Ported from Kotlin's GraphStateManager.kt with Python async patterns.

Key features:
- Thread-safe state management using asyncio locks
- Automatic action application
- Session cleanup for horizontal scaling readiness
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from .schemas import (
    ActionType,
    GraphEdge,
    GraphNode,
    GraphState,
    SketchAction,
)

logger = logging.getLogger(__name__)


class SessionState:
    """State for a single user session."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.graph = GraphState()
        self.canvas_snapshot: Optional[str] = None
        self.last_activity = datetime.utcnow()
        self.lock = asyncio.Lock()
    
    def touch(self) -> None:
        """Update last activity time."""
        self.last_activity = datetime.utcnow()
    
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """Check if session has expired."""
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        return self.last_activity < cutoff


class StateManager:
    """
    Manages graph state for all user sessions.
    
    This is the Python equivalent of Kotlin's GraphStateManager.
    Uses asyncio locks for thread-safe concurrent access.
    
    Note: For horizontal scaling, this should be backed by Redis.
    Currently uses in-memory storage (single instance only).
    """
    
    def __init__(self):
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()
        logger.info("StateManager initialized (in-memory mode)")
    
    async def get_or_create(self, user_id: str) -> SessionState:
        """Get existing session or create a new one."""
        async with self._lock:
            if user_id not in self._sessions:
                self._sessions[user_id] = SessionState(user_id)
                logger.info(f"Created new session for user {user_id}")
            
            session = self._sessions[user_id]
            session.touch()
            return session
    
    async def get(self, user_id: str) -> Optional[SessionState]:
        """Get session if it exists."""
        async with self._lock:
            session = self._sessions.get(user_id)
            if session:
                session.touch()
            return session
    
    async def remove(self, user_id: str) -> None:
        """Remove a session."""
        async with self._lock:
            if user_id in self._sessions:
                del self._sessions[user_id]
                logger.info(f"Removed session for user {user_id}")
    
    async def apply_action(self, user_id: str, action: SketchAction) -> bool:
        """
        Apply a single action to the user's graph state.
        
        Returns True if action was applied successfully.
        This is the core logic ported from Kotlin's GraphState.applyAction().
        """
        session = await self.get(user_id)
        if not session:
            logger.warning(f"No session found for user {user_id}")
            return False
        
        async with session.lock:
            graph = session.graph
            
            try:
                if action.action == ActionType.CREATE_NODE:
                    if not action.label or not action.type:
                        logger.warning(f"create_node missing label or type: {action}")
                        return False
                    
                    graph.nodes[action.id] = GraphNode(
                        id=action.id,
                        label=action.label,
                        description=action.description or "",
                        type=action.type,
                        parent_id=action.parent_id,
                        color=action.color,
                        position=action.position,
                        relative_to=action.relative_to,
                        opacity=action.opacity,
                    )
                    logger.debug(f"Created node: {action.id}")
                    return True
                
                elif action.action == ActionType.UPDATE_NODE:
                    if action.id not in graph.nodes:
                        logger.warning(f"update_node: node {action.id} not found")
                        return False
                    
                    existing = graph.nodes[action.id]
                    # Use explicit None checks for ALL optional fields
                    # This ensures empty string "" or 0 values are properly applied
                    graph.nodes[action.id] = GraphNode(
                        id=action.id,
                        label=action.label if action.label is not None else existing.label,
                        description=action.description if action.description is not None else existing.description,
                        type=action.type if action.type is not None else existing.type,
                        parent_id=action.parent_id if action.parent_id is not None else existing.parent_id,
                        color=action.color if action.color is not None else existing.color,
                        position=action.position if action.position is not None else existing.position,
                        relative_to=action.relative_to if action.relative_to is not None else existing.relative_to,
                        opacity=action.opacity if action.opacity is not None else existing.opacity,
                    )
                    logger.debug(f"Updated node: {action.id}")
                    return True
                
                elif action.action == ActionType.DELETE_NODE:
                    if action.id not in graph.nodes:
                        logger.warning(f"delete_node: node {action.id} not found")
                        return False
                    
                    # Delete the node
                    del graph.nodes[action.id]
                    
                    # Remove connected edges
                    graph.edges = [
                        e for e in graph.edges
                        if e.source_id != action.id and e.target_id != action.id
                    ]
                    
                    # Remove child nodes (if this was a frame)
                    children_to_remove = [
                        nid for nid, node in graph.nodes.items()
                        if node.parent_id == action.id
                    ]
                    for child_id in children_to_remove:
                        del graph.nodes[child_id]
                    
                    logger.debug(f"Deleted node: {action.id} (and {len(children_to_remove)} children)")
                    return True
                
                elif action.action == ActionType.CREATE_EDGE:
                    if not action.source_id or not action.target_id:
                        logger.warning(f"create_edge missing source_id or target_id: {action}")
                        return False
                    
                    # Check if source and target exist
                    if action.source_id not in graph.nodes:
                        logger.warning(f"create_edge: source {action.source_id} not found")
                        return False
                    if action.target_id not in graph.nodes:
                        logger.warning(f"create_edge: target {action.target_id} not found")
                        return False
                    
                    # Check for duplicate
                    for edge in graph.edges:
                        if edge.source_id == action.source_id and edge.target_id == action.target_id:
                            logger.debug(f"Edge already exists: {action.source_id} -> {action.target_id}")
                            return True  # Already exists, not an error
                    
                    graph.edges.append(GraphEdge(
                        source_id=action.source_id,
                        target_id=action.target_id,
                        bidirectional=action.bidirectional or False,
                    ))
                    logger.debug(f"Created edge: {action.source_id} -> {action.target_id}")
                    return True
                
                elif action.action == ActionType.DELETE_EDGE:
                    if not action.source_id or not action.target_id:
                        logger.warning(f"delete_edge missing source_id or target_id: {action}")
                        return False
                    
                    original_count = len(graph.edges)
                    graph.edges = [
                        e for e in graph.edges
                        if not (e.source_id == action.source_id and e.target_id == action.target_id)
                    ]
                    
                    if len(graph.edges) < original_count:
                        logger.debug(f"Deleted edge: {action.source_id} -> {action.target_id}")
                        return True
                    else:
                        logger.warning(f"delete_edge: edge not found")
                        return False
                
                else:
                    logger.warning(f"Unknown action type: {action.action}")
                    return False
            
            except Exception as e:
                logger.error(f"Error applying action {action}: {e}")
                return False
    
    async def add_to_history(self, user_id: str, command: str) -> None:
        """Add a command to the conversation history."""
        session = await self.get(user_id)
        if session:
            async with session.lock:
                session.graph.conversation_history.append(command)
                # Keep only last 10 commands
                if len(session.graph.conversation_history) > 10:
                    session.graph.conversation_history = session.graph.conversation_history[-10:]
    
    async def cleanup_expired(self, timeout_minutes: int = 60) -> int:
        """Clean up expired sessions. Returns count of removed sessions."""
        async with self._lock:
            expired_users = [
                uid for uid, session in self._sessions.items()
                if session.is_expired(timeout_minutes)
            ]
            
            for uid in expired_users:
                del self._sessions[uid]
            
            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired sessions")
            
            return len(expired_users)
    
    @property
    def active_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)


# Global state manager instance
state_manager = StateManager()
