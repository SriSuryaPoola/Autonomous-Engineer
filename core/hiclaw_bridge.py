"""
HiClaw OS Integration Layer.

Abstracts HiClaw primitives — Matrix rooms, messaging, agent registry,
and coordination — so that all inter-agent communication flows through
the HiClaw coordination system.

HiClaw Architecture:
    - Agents communicate via Matrix-style rooms
    - Manager coordinates workers through HiClaw messaging
    - All task assignments, progress updates, and outputs are routed
      through the HiClaw bridge
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.message import AgentMessage

logger = logging.getLogger(__name__)


# ─── HiClaw Room ──────────────────────────────────────────────────────────────

class RoomType(Enum):
    """Types of HiClaw communication rooms."""
    BROADCAST = "broadcast"      # Manager → all workers
    DIRECT = "direct"            # 1-to-1 between manager and worker
    REVIEW = "review"            # Code review channel
    STATUS = "status"            # Status/progress updates


@dataclass
class HiClawRoom:
    """
    A Matrix-style room for agent communication.

    Rooms provide isolated channels for structured messaging between
    agents in the HiClaw system.
    """

    room_id: str = field(default_factory=lambda: f"room_{uuid.uuid4().hex[:12]}")
    name: str = ""
    room_type: RoomType = RoomType.DIRECT
    members: list[str] = field(default_factory=list)  # agent_ids
    messages: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def add_member(self, agent_id: str) -> None:
        if agent_id not in self.members:
            self.members.append(agent_id)

    def post_message(self, sender_id: str, content: Any) -> dict:
        """Post a message to this room."""
        msg = {
            "msg_id": str(uuid.uuid4()),
            "room_id": self.room_id,
            "sender_id": sender_id,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        self.messages.append(msg)
        return msg

    def get_messages(self, since: Optional[datetime] = None,
                     sender_id: Optional[str] = None) -> list[dict]:
        """Retrieve messages, optionally filtered."""
        msgs = self.messages
        if since:
            since_iso = since.isoformat()
            msgs = [m for m in msgs if m["timestamp"] >= since_iso]
        if sender_id:
            msgs = [m for m in msgs if m["sender_id"] == sender_id]
        return msgs

    def __repr__(self) -> str:
        return f"HiClawRoom({self.name!r}, type={self.room_type.value}, members={len(self.members)})"


# ─── HiClaw Agent Registry ───────────────────────────────────────────────────

@dataclass
class AgentRegistration:
    """Registration record for an agent in the HiClaw system."""
    agent_id: str
    role: str
    capabilities: list[str] = field(default_factory=list)
    status: str = "idle"          # idle | busy | offline
    registered_at: datetime = field(default_factory=datetime.now)


class HiClawAgentRegistry:
    """
    Central registry for discovering and managing HiClaw agents.
    """

    def __init__(self):
        self._agents: dict[str, AgentRegistration] = {}
        self._role_index: dict[str, list[str]] = defaultdict(list)
        self._logger = logging.getLogger("hiclaw.registry")

    def register(self, agent_id: str, role: str,
                 capabilities: Optional[list[str]] = None) -> AgentRegistration:
        """Register an agent with the HiClaw system."""
        reg = AgentRegistration(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities or [],
        )
        self._agents[agent_id] = reg
        self._role_index[role].append(agent_id)
        self._logger.info(f"Registered agent: {role} ({agent_id[:8]})")
        return reg

    def unregister(self, agent_id: str) -> None:
        reg = self._agents.pop(agent_id, None)
        if reg:
            self._role_index[reg.role] = [
                a for a in self._role_index[reg.role] if a != agent_id
            ]

    def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        return self._agents.get(agent_id)

    def find_by_role(self, role: str) -> list[AgentRegistration]:
        return [self._agents[aid] for aid in self._role_index.get(role, [])
                if aid in self._agents]

    def set_status(self, agent_id: str, status: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].status = status

    @property
    def all_agents(self) -> list[AgentRegistration]:
        return list(self._agents.values())

    @property
    def available_roles(self) -> list[str]:
        return list(self._role_index.keys())


# ─── HiClaw Messenger ────────────────────────────────────────────────────────

class HiClawMessenger:
    """
    Message routing system for HiClaw agents.

    Handles sending/receiving structured messages between agents via
    rooms, with support for callbacks and async delivery.
    """

    def __init__(self, registry: HiClawAgentRegistry):
        self.registry = registry
        self._rooms: dict[str, HiClawRoom] = {}
        self._agent_rooms: dict[str, list[str]] = defaultdict(list)  # agent_id → room_ids
        self._callbacks: dict[str, list[Callable]] = defaultdict(list)
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._logger = logging.getLogger("hiclaw.messenger")

    def create_room(self, name: str, room_type: RoomType,
                    members: Optional[list[str]] = None) -> HiClawRoom:
        """Create a new communication room."""
        room = HiClawRoom(name=name, room_type=room_type)
        for member in (members or []):
            room.add_member(member)
            self._agent_rooms[member].append(room.room_id)
        self._rooms[room.room_id] = room
        self._logger.info(
            f"Created room: {name} ({room_type.value}) "
            f"with {len(room.members)} members"
        )
        return room

    def get_room(self, room_id: str) -> Optional[HiClawRoom]:
        return self._rooms.get(room_id)

    def get_rooms_for_agent(self, agent_id: str) -> list[HiClawRoom]:
        return [self._rooms[rid] for rid in self._agent_rooms.get(agent_id, [])
                if rid in self._rooms]

    async def send_message(self, sender_id: str, room_id: str,
                           content: Any) -> dict:
        """
        Send a structured message to a room.

        The content should be an AgentMessage.to_dict() or any
        JSON-serializable payload.
        """
        room = self._rooms.get(room_id)
        if not room:
            raise ValueError(f"Room {room_id} not found")
        if sender_id not in room.members:
            raise PermissionError(f"Agent {sender_id[:8]} is not a member of room {room.name}")

        msg = room.post_message(sender_id, content)
        self._logger.debug(
            f"[{room.name}] {sender_id[:8]} → message {msg['msg_id'][:8]}"
        )

        # Notify callbacks
        for cb in self._callbacks.get(room_id, []):
            try:
                await cb(msg)
            except Exception as exc:
                self._logger.error(f"Callback error in room {room.name}: {exc}")

        return msg

    async def broadcast(self, sender_id: str, content: Any) -> list[dict]:
        """Broadcast a message to all rooms the sender is in."""
        results = []
        for room_id in self._agent_rooms.get(sender_id, []):
            room = self._rooms.get(room_id)
            if room and room.room_type == RoomType.BROADCAST:
                msg = await self.send_message(sender_id, room_id, content)
                results.append(msg)
        return results

    def on_message(self, room_id: str, callback: Callable) -> None:
        """Register a callback for messages in a room."""
        self._callbacks[room_id].append(callback)

    def get_messages(self, room_id: str,
                     since: Optional[datetime] = None) -> list[dict]:
        room = self._rooms.get(room_id)
        return room.get_messages(since=since) if room else []


# ─── HiClaw Coordinator ──────────────────────────────────────────────────────

class HiClawCoordinator:
    """
    Top-level HiClaw coordination system.

    Ties together the registry, messenger, and rooms to provide
    a complete orchestration interface.
    """

    def __init__(self):
        self.registry = HiClawAgentRegistry()
        self.messenger = HiClawMessenger(self.registry)
        self._task_rooms: dict[str, HiClawRoom] = {}   # task_id → room
        self._broadcast_room: Optional[HiClawRoom] = None
        self._status_room: Optional[HiClawRoom] = None
        self._review_room: Optional[HiClawRoom] = None
        self._logger = logging.getLogger("hiclaw.coordinator")

    # ── Setup ─────────────────────────────────────────────────────────────

    def initialize(self, manager_id: str, worker_ids: list[str]) -> None:
        """
        Initialize the HiClaw environment with standard rooms.
        """
        all_ids = [manager_id] + worker_ids

        # Broadcast room (Manager → all)
        self._broadcast_room = self.messenger.create_room(
            "🔊 Broadcast", RoomType.BROADCAST, all_ids
        )

        # Status room (anyone → status updates)
        self._status_room = self.messenger.create_room(
            "📊 Status", RoomType.STATUS, all_ids
        )

        # Review room
        self._review_room = self.messenger.create_room(
            "🔍 Review", RoomType.REVIEW, all_ids
        )

        # Direct rooms (Manager ↔ each worker)
        for wid in worker_ids:
            self.messenger.create_room(
                f"📨 Manager↔{wid[:8]}", RoomType.DIRECT, [manager_id, wid]
            )

        self._logger.info(
            f"HiClaw initialized: {len(all_ids)} agents, "
            f"{len(self.messenger._rooms)} rooms"
        )

    def get_direct_room(self, agent_a: str, agent_b: str) -> Optional[HiClawRoom]:
        """Find the direct room between two agents."""
        rooms_a = set(self.messenger._agent_rooms.get(agent_a, []))
        rooms_b = set(self.messenger._agent_rooms.get(agent_b, []))
        shared = rooms_a & rooms_b
        for rid in shared:
            room = self.messenger.get_room(rid)
            if room and room.room_type == RoomType.DIRECT:
                return room
        return None

    @property
    def broadcast_room(self) -> Optional[HiClawRoom]:
        return self._broadcast_room

    @property
    def status_room(self) -> Optional[HiClawRoom]:
        return self._status_room

    @property
    def review_room(self) -> Optional[HiClawRoom]:
        return self._review_room

    # ── Task Lifecycle ────────────────────────────────────────────────────

    def create_task_room(self, task_id: str, participants: list[str]) -> HiClawRoom:
        """Create a dedicated room for a specific task."""
        room = self.messenger.create_room(
            f"📋 Task-{task_id[:8]}", RoomType.DIRECT, participants
        )
        self._task_rooms[task_id] = room
        return room

    def get_task_room(self, task_id: str) -> Optional[HiClawRoom]:
        return self._task_rooms.get(task_id)

    async def post_status(self, agent_id: str, status_text: str) -> None:
        """Post a status update to the status room."""
        if self._status_room:
            await self.messenger.send_message(
                agent_id,
                self._status_room.room_id,
                {"type": "status_update", "text": status_text},
            )

    async def post_review(self, agent_id: str, review_content: Any) -> None:
        """Post to the review room."""
        if self._review_room:
            await self.messenger.send_message(
                agent_id,
                self._review_room.room_id,
                {"type": "review", "content": review_content},
            )

    def summary(self) -> str:
        agents = self.registry.all_agents
        rooms = len(self.messenger._rooms)
        return (
            f"HiClaw System: {len(agents)} agents, {rooms} rooms\n"
            + "\n".join(f"  • {a.role} ({a.agent_id[:8]}) [{a.status}]" for a in agents)
        )
