"""
WebSocket Connection Manager
Handles real-time connections for AI-moderated conversations
"""
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime


class ConnectionManager:
    """Manages WebSocket connections for real-time AI moderation"""

    def __init__(self):
        # Active connections: {user_id: WebSocket}
        self.active_connections: Dict[int, WebSocket] = {}

        # Session participants: {session_id: {user1_id, user2_id}}
        self.session_participants: Dict[str, Set[int]] = {}

        # User to session mapping: {user_id: session_id}
        self.user_sessions: Dict[int, str] = {}

    async def connect(self, websocket: WebSocket, user_id: int, session_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_sessions[user_id] = session_id

        # Add to session participants
        if session_id not in self.session_participants:
            self.session_participants[session_id] = set()
        self.session_participants[session_id].add(user_id)

        print(f"✅ User {user_id} connected to session {session_id}")

    def disconnect(self, user_id: int):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]

        # Remove from session
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]
            if session_id in self.session_participants:
                self.session_participants[session_id].discard(user_id)

                # Clean up empty sessions
                if not self.session_participants[session_id]:
                    del self.session_participants[session_id]

            del self.user_sessions[user_id]

        print(f"❌ User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to a specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                print(f"Error sending to user {user_id}: {e}")
                self.disconnect(user_id)

    async def send_to_session(self, message: dict, session_id: str, exclude_user: Optional[int] = None):
        """Send message to all users in a session (optionally excluding one)"""
        if session_id not in self.session_participants:
            return

        tasks = []
        for user_id in self.session_participants[session_id]:
            if exclude_user and user_id == exclude_user:
                continue
            tasks.append(self.send_personal_message(message, user_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_to_session(self, message: dict, session_id: str):
        """Broadcast message to all users in a session"""
        await self.send_to_session(message, session_id)

    def is_user_connected(self, user_id: int) -> bool:
        """Check if user is connected"""
        return user_id in self.active_connections

    def get_session_participants(self, session_id: str) -> Set[int]:
        """Get all participants in a session"""
        return self.session_participants.get(session_id, set())

    def get_user_session(self, user_id: int) -> Optional[str]:
        """Get session ID for a user"""
        return self.user_sessions.get(user_id)


# Global connection manager instance
manager = ConnectionManager()
