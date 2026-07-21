"""GitHub App webhook (Milestone 7).

``POST /api/github/webhook`` verifies the HMAC signature, routes by event/action,
and returns fast (202) while the analysis runs in a background task:
fetch diff -> analyze (shared pipeline) -> persist -> optionally post one review.

Safety:
- The signature is verified before the body is parsed; failures return 401.
- PR content is untrusted: it's analyzed as data, never executed, and the review
  is schema-validated + score-clamped upstream before we render it.
- Posting is gated by ``POST_REVIEWS`` (dry-run by default) and limited to one
  review per PR; the default event is ``COMMENT``, never ``REQUEST_CHANGES``.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.db.repository import persist_analysis
from app.db.session import get_session_factory
from app.github.client import GitHubClient, build_installation_client
from app.github.render import render_review_comment
from app.github.webhook import (
    HANDLED_ACTIONS,
    pr_metadata_from_payload,
    pr_ref_from_payload,
    verify_signature,
)
from app.pipeline import analyze_diff

logger = get_logger("app.api.webhook")

router = APIRouter(prefix="/api/github", tags=["github"])


@router.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session_factory: Annotated[sessionmaker[Session], Depends(get_session_factory)],
) -> Response:
    """Receive a GitHub webhook: verify, filter, and schedule analysis."""
    settings = get_settings()
    body = await request.body()

    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(body, signature, settings.github_webhook_secret):
        # Do not reveal which part failed; never log the secret or signature.
        raise HTTPException(status_code=401, detail="invalid or missing signature")

    event = request.headers.get("X-GitHub-Event", "")
    if event == "ping":
        return JSONResponse({"msg": "pong"})
    if event != "pull_request":
        return Response(status_code=204)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid JSON body") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid payload")

    action = str(payload.get("action") or "")
    if action not in HANDLED_ACTIONS:
        return Response(status_code=204)

    pr = payload.get("pull_request")
    if not isinstance(pr, dict) or pr.get("number") is None:
        raise HTTPException(status_code=400, detail="malformed pull_request payload")

    ref = pr_ref_from_payload(payload)
    background_tasks.add_task(
        handle_pull_request_event,
        payload,
        settings=settings,
        session_factory=session_factory,
    )
    logger.info(
        "accepted pull_request webhook",
        extra={"repo": ref.full_name, "number": ref.number, "action": action},
    )
    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "action": action, "number": ref.number},
    )


def handle_pull_request_event(
    payload: dict[str, Any],
    *,
    settings: Settings,
    session_factory: sessionmaker[Session] | None = None,
    client: GitHubClient | None = None,
) -> None:
    """Analyze a PR and persist it; post one review when enabled.

    Runs off the request path (background task). Each stage degrades gracefully so
    one failure (GitHub, DB, or posting) never takes down the others. ``client``
    is injectable for tests; in production it's built from the installation id.
    """
    ref = pr_ref_from_payload(payload)
    metadata = pr_metadata_from_payload(payload)

    try:
        if client is None:
            if ref.installation_id is None:
                logger.warning(
                    "no installation id in payload; cannot authenticate",
                    extra={"repo": ref.full_name, "number": ref.number},
                )
                return
            client = build_installation_client(settings, ref.installation_id)
        diff_text = client.get_pull_request_diff(ref.owner, ref.repo, ref.number)
    except Exception as exc:  # network / auth / HTTP error
        logger.warning(
            "failed to fetch PR diff",
            extra={"error": str(exc), "repo": ref.full_name, "number": ref.number},
        )
        return

    artifacts = analyze_diff(metadata, diff_text, settings)

    factory = session_factory or get_session_factory()
    session = factory()
    try:
        persist_analysis(
            session,
            metadata=metadata,
            parsed=artifacts.parsed,
            risk=artifacts.risk,
            review_outcome=artifacts.review,
            vector=artifacts.vector,
            embedding_provider_name=artifacts.embedding_provider_name,
            embedding_model=artifacts.embedding_model,
            latency_ms=artifacts.latency_ms,
        )
    except SQLAlchemyError as exc:
        session.rollback()
        logger.warning(
            "persistence unavailable for webhook analysis",
            extra={"error": str(exc), "repo": ref.full_name, "number": ref.number},
        )
    finally:
        session.close()

    if not settings.post_reviews:
        logger.info(
            "dry-run: analysis stored, not posting review",
            extra={"repo": ref.full_name, "number": ref.number},
        )
        return

    try:
        if client.has_prism_review(ref.owner, ref.repo, ref.number):
            logger.info(
                "existing PRism review found; skipping post",
                extra={"repo": ref.full_name, "number": ref.number},
            )
            return
        body = render_review_comment(artifacts.review.review)
        client.create_review(ref.owner, ref.repo, ref.number, body=body, event="COMMENT")
        logger.info(
            "posted PRism review",
            extra={
                "repo": ref.full_name,
                "number": ref.number,
                "status": artifacts.review.status,
            },
        )
    except Exception as exc:  # posting is best-effort; never crash the worker
        logger.warning(
            "failed to post review",
            extra={"error": str(exc), "repo": ref.full_name, "number": ref.number},
        )
