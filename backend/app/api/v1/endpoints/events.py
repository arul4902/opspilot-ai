import uuid
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from backend.app.core.broadcaster import EventBroadcaster

router = APIRouter()


@router.get("/stream")
async def stream_operational_events(request: Request):
    """
    Server-Sent Events (SSE) feed for live operational dashboard updates.
    Streams real-time events for order changes, support tickets, approval requests,
    and autonomous agent actions across connected operators.
    """
    client_id = str(uuid.uuid4())[:8]

    return StreamingResponse(
        EventBroadcaster.stream_events(client_id=client_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disables proxy buffering for Nginx/Cloudflare
            "Access-Control-Allow-Origin": "*",
        }
    )

