"""FastAPI router exposing `/api/realtime/subscribe` (SSE)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from orbiteus_core.context import RequestContext
from orbiteus_core.realtime import stream_topics, topic_is_allowed
from orbiteus_core.security.middleware import require_auth

router = APIRouter(prefix="/api/realtime", tags=["realtime"])


@router.get("/subscribe")
async def subscribe(
    request: Request,
    topic: list[str] = Query(default=[]),
    ctx: RequestContext = Depends(require_auth),
):
    """Stream Server-Sent Events for one or more topics.

    Topics must match the caller's tenant unless the caller is a superadmin.
    """
    if not topic:
        raise HTTPException(status_code=400, detail="At least one ?topic= is required")

    forbidden = [t for t in topic if not topic_is_allowed(ctx, t)]
    if forbidden:
        raise HTTPException(
            status_code=403,
            detail={"code": "realtime.topic_forbidden", "topics": forbidden},
        )

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        stream_topics(topic),
        media_type="text/event-stream",
        headers=headers,
    )
