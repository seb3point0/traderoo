"""
WebSocket endpoint for real-time updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import asyncio
import json
from datetime import datetime

from app.utils.logger import log
from app.core.event_bus import get_event_bus, EventType, Event

router = APIRouter()

# Connected WebSocket clients
connected_clients: Set[WebSocket] = set()


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        log.info(f"WebSocket client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection"""
        self.active_connections.discard(websocket)
        log.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            log.error(f"Error sending message to client: {e}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                log.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)


manager = ConnectionManager()


async def event_broadcaster():
    """Subscribe to event bus and broadcast to WebSocket clients"""
    event_bus = get_event_bus()
    
    async def handle_event(event: Event):
        """Handle events from event bus"""
        message = {
            "type": event.event_type.value,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
            "source": event.source
        }
        await manager.broadcast(message)
    
    # Subscribe to all relevant events
    event_types = [
        EventType.ORDER_CREATED,
        EventType.ORDER_FILLED,
        EventType.ORDER_CANCELLED,
        EventType.POSITION_OPENED,
        EventType.POSITION_CLOSED,
        EventType.POSITION_UPDATED,
        EventType.SIGNAL_BUY,
        EventType.SIGNAL_SELL,
        EventType.RISK_LIMIT_HIT
    ]
    
    for event_type in event_types:
        event_bus.subscribe(event_type, handle_event)


@router.on_event("startup")
async def startup_event():
    """Start event broadcaster on startup"""
    asyncio.create_task(event_broadcaster())
    log.info("WebSocket event broadcaster started")


@router.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        await manager.send_personal_message(
            {
                "type": "connection",
                "message": "Connected to Trading Bot WebSocket",
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive messages from client (if any)
                data = await websocket.receive_text()
                
                # Parse and handle client messages
                try:
                    message = json.loads(data)
                    
                    # Handle ping/pong for keepalive
                    if message.get("type") == "ping":
                        await manager.send_personal_message(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                            websocket
                        )
                    
                except json.JSONDecodeError:
                    log.warning(f"Invalid JSON received: {data}")
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                log.error(f"WebSocket error: {e}")
                break
    
    finally:
        manager.disconnect(websocket)


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return {
        "connected_clients": len(manager.active_connections),
        "status": "active"
    }

