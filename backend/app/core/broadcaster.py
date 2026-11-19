import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, AsyncGenerator, Set
from backend.app.core.logging import logger


class EventBroadcaster:
    """
    In-memory async Pub/Sub event broadcaster for real-time Server-Sent Events (SSE).
    Distributes domain events (orders, approvals, tickets, agent telemetry)
    across all connected operator consoles.
    """
    _subscribers: Set[asyncio.Queue] = set()

    @classmethod
    def subscribe(cls) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        cls._subscribers.add(queue)
        logger.info(f"[SSE Broadcaster] Client subscribed. Active listeners: {len(cls._subscribers)}")
        return queue

    @classmethod
    def unsubscribe(cls, queue: asyncio.Queue):
        if queue in cls._subscribers:
            cls._subscribers.remove(queue)
            logger.info(f"[SSE Broadcaster] Client unsubscribed. Remaining listeners: {len(cls._subscribers)}")

    @classmethod
    def broadcast(cls, event_type: str, data: Dict[str, Any]):
        """
        Broadcast an event to all active SSE queues non-blockingly.
        """
        payload = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        for q in list(cls._subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("[SSE Broadcaster] Subscriber queue full; dropping event.")
            except Exception as e:
                logger.error(f"[SSE Broadcaster] Error pushing to subscriber: {e}")

    @classmethod
    async def stream_events(cls, client_id: str = "anon") -> AsyncGenerator[str, None]:
        queue = cls.subscribe()
        try:
            # Yield initial connection confirmation event
            init_payload = json.dumps({
                "type": "system.connected",
                "client_id": client_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            yield f"event: system.connected\ndata: {init_payload}\n\n"

            while True:
                try:
                    # Wait for next event or send ping every 15 seconds to keep connection alive
                    event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"id: {event_data['id']}\nevent: {event_data['type']}\ndata: {json.dumps(event_data['data'])}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat keepalive ping to prevent proxy/browser timeout
                    yield f": keepalive {datetime.now(timezone.utc).isoformat()}\n\n"
        except asyncio.CancelledError:
            logger.info(f"[SSE Broadcaster] Client {client_id} disconnected.")
        finally:
            cls.unsubscribe(queue)

