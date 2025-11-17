"""
PHRONAI Pydantic Schemas

These schemas enforce zero-hallucination by strictly validating LLM output.
Ported from VoiceBoard's sketch-protocol.md with added Python type safety.

The key insight: By using Pydantic with Instructor, we force the LLM to output
ONLY valid, schema-compliant JSON. Invalid outputs are automatically retried.
"""

from enum import Enum
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class ActionType(str, Enum):
    """Valid action types for the agent."""
    CREATE_NODE = "create_node"
    UPDATE_NODE = "update_node"
    DELETE_NODE = "delete_node"
    CREATE_EDGE = "create_edge"
    DELETE_EDGE = "delete_edge"


class NodeType(str, Enum):
    """
    Valid node types.
    
    Semantic types (preferred for tech diagrams):
    - database, server, client, storage, network
    
    Shape types (for general concepts):
    - frame, cloud, person, process, data, diamond, hexagon, box, circle, text, note
    """
    # Semantic types
    DATABASE = "database"
    SERVER = "server"
    CLIENT = "client"
    STORAGE = "storage"
    NETWORK = "network"
    
    # Shape types
    FRAME = "frame"
    CLOUD = "cloud"
    PERSON = "person"
    PROCESS = "process"
    DATA = "data"
    DIAMOND = "diamond"
    HEXAGON = "hexagon"
    BOX = "box"
    CIRCLE = "circle"
    TEXT = "text"
    NOTE = "note"


class NoteColor(str, Enum):
    """Valid colors for nodes/notes. Comprehensive palette."""
    # Primary colors
    YELLOW = "yellow"
    PINK = "pink"
    BLUE = "blue"
    GREEN = "green"
    ORANGE = "orange"
    RED = "red"
    VIOLET = "violet"
    PURPLE = "purple"
    # Light variants
    LIGHT_BLUE = "light-blue"
    LIGHT_GREEN = "light-green"
    LIGHT_VIOLET = "light-violet"
    LIGHT_RED = "light-red"
    LIGHT_YELLOW = "light-yellow"
    # Neutral colors
    BLACK = "black"
    WHITE = "white"
    GRAY = "gray"
    GREY = "grey"
    # Other colors
    CYAN = "cyan"
    TEAL = "teal"
    MAGENTA = "magenta"
    BROWN = "brown"


class Position(str, Enum):
    """Valid relative positions."""
    ABOVE = "above"
    BELOW = "below"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


class SketchAction(BaseModel):
    """
    A single action to modify the graph/canvas.
    
    This is the core schema that the LLM must output.
    Using Pydantic validation ensures zero hallucinations.
    """
    action: ActionType = Field(
        description="The type of action to perform"
    )
    id: str = Field(
        description="Unique identifier for the node/edge. Use snake_case."
    )
    
    # Node properties (for create_node, update_node)
    label: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Short main title (2-4 words)"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Brief detail (3-8 words)"
    )
    type: Optional[NodeType] = Field(
        default=None,
        description="The semantic or shape type of the node"
    )
    color: Optional[NoteColor] = Field(
        default=None,
        description="Color for notes/sticky notes"
    )
    opacity: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Transparency: 1.0=opaque, 0.5=half transparent"
    )
    position: Optional[Position] = Field(
        default=None,
        description="Relative position for text/notes"
    )
    relative_to: Optional[str] = Field(
        default=None,
        description="Node ID to position relative to"
    )
    parent_id: Optional[str] = Field(
        default=None,
        description="Frame ID for grouping nodes inside frames"
    )
    
    # Edge properties (for create_edge, delete_edge)
    source_id: Optional[str] = Field(
        default=None,
        description="Source node ID for edges"
    )
    target_id: Optional[str] = Field(
        default=None,
        description="Target node ID for edges"
    )
    bidirectional: Optional[bool] = Field(
        default=False,
        description="Whether the edge has arrows on both ends"
    )

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure IDs are in snake_case and reasonable length."""
        if not v or len(v) > 50:
            raise ValueError("ID must be 1-50 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("ID must be alphanumeric with underscores/hyphens")
        return v.lower()


class SketchResponse(BaseModel):
    """
    Complete response from the LLM.
    
    Contains a list of actions to apply to the graph.
    """
    actions: list[SketchAction] = Field(
        description="List of actions to perform on the graph"
    )


class GraphNode(BaseModel):
    """
    A node in the graph state.
    Ported from Kotlin's GraphNode data class.
    Note: color is str (not NoteColor) to accept any color from frontend.
    """
    id: str
    label: str
    description: str = ""
    type: NodeType
    parent_id: Optional[str] = None
    color: Optional[str] = None  # Accept any string for flexibility
    position: Optional[Position] = None
    relative_to: Optional[str] = None
    opacity: Optional[float] = None


class GraphEdge(BaseModel):
    """
    An edge (connection) between two nodes.
    Ported from Kotlin's GraphEdge data class.
    Accepts both snake_case and camelCase from frontend.
    """
    id: Optional[str] = None
    source_id: Optional[str] = Field(default=None, alias="sourceId")
    target_id: Optional[str] = Field(default=None, alias="targetId")
    bidirectional: bool = False
    
    model_config = {"populate_by_name": True}
    
    @model_validator(mode="before")
    @classmethod
    def handle_camel_case(cls, data):
        """Handle both snake_case and camelCase field names."""
        if isinstance(data, dict):
            # Map camelCase to snake_case if needed
            if "sourceId" in data and "source_id" not in data:
                data["source_id"] = data.pop("sourceId")
            if "targetId" in data and "target_id" not in data:
                data["target_id"] = data.pop("targetId")
        return data


class GraphState(BaseModel):
    """
    Complete state of the graph.
    Ported from Kotlin's GraphState class.
    Accepts nodes as dict or list (from frontend).
    """
    nodes: Union[dict[str, GraphNode], list[dict]] = Field(default_factory=dict)
    edges: list[GraphEdge] = Field(default_factory=list)
    conversation_history: list[str] = Field(default_factory=list)
    
    @model_validator(mode="before")
    @classmethod
    def normalize_nodes(cls, data):
        """Convert nodes list to dict if needed."""
        if isinstance(data, dict) and "nodes" in data:
            nodes = data.get("nodes", {})
            if isinstance(nodes, list):
                # Convert list to dict keyed by id
                data["nodes"] = {n.get("id", str(i)): n for i, n in enumerate(nodes)}
        return data
    
    def to_summary(self) -> str:
        """Generate a summary for LLM context."""
        nodes_dict = self.nodes if isinstance(self.nodes, dict) else {}
        if not nodes_dict:
            return "Empty graph - no nodes yet."
        
        node_summaries = []
        for node_id, node in nodes_dict.items():
            if isinstance(node, GraphNode):
                node_summaries.append(f"- {node.id}: {node.label} ({node.type.value})")
            elif isinstance(node, dict):
                label = node.get("label", "Unknown")
                ntype = node.get("type", "box")
                node_summaries.append(f"- {node_id}: {label} ({ntype})")
        
        edge_summaries = [
            f"- {e.source_id} -> {e.target_id}"
            for e in self.edges if e.source_id and e.target_id
        ]
        
        summary = f"Nodes ({len(nodes_dict)}):\n" + "\n".join(node_summaries)
        if edge_summaries:
            summary += f"\n\nEdges ({len(self.edges)}):\n" + "\n".join(edge_summaries)
        
        return summary
    
    def get_history_summary(self, max_entries: int = 5) -> str:
        """Get recent conversation history for context."""
        if not self.conversation_history:
            return "No previous commands."
        
        recent = self.conversation_history[-max_entries:]
        return "Recent commands:\n" + "\n".join(f"- {cmd}" for cmd in recent)


class CanvasSyncMessage(BaseModel):
    """
    Message from client to sync canvas state.
    Ported from Kotlin's CanvasSyncMessage.
    """
    type: Literal["canvas_sync"] = "canvas_sync"
    snapshot: str = Field(description="Full tldraw canvas JSON snapshot")
    graph: GraphState = Field(description="Extracted graph state")


class FeedbackMessage(BaseModel):
    """
    User feedback for self-learning.
    This is the "Self-Learning Agent" feature for Giga AI.
    """
    type: Literal["feedback"] = "feedback"
    session_id: str
    action_id: str
    feedback_type: Literal["undo", "edit", "correct", "approve"]
    original_action: Optional[SketchAction] = None
    corrected_action: Optional[SketchAction] = None
    user_comment: Optional[str] = None
