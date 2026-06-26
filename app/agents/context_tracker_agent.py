"""
Context Tracker Agent for multi-turn conversation management.

Tracks conversation history, entity mentions, and provides context-aware routing hints.
Includes automatic background cleanup to prevent memory leaks.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.agents.quality_config import (
    CONTEXT_MAX_HISTORY_TURNS,
    CONTEXT_SUMMARY_FREQUENCY,
    CONTEXT_SUMMARY_MIN_TURNS,
    CONTEXT_TTL_SECONDS,
)
from app.agents.quality_models import (
    ConversationContext,
    ConversationTurn,
    ContextHints,
)

logger = logging.getLogger(__name__)


# ============================================================================
# In-Memory Storage
# ============================================================================

# Production would use Redis with proper serialization
_context_store: Dict[str, ConversationContext] = {}
_cleanup_task: Optional[asyncio.Task] = None


# ============================================================================
# Background Cleanup Task (P1-6 fix)
# ============================================================================

async def _background_cleanup_loop():
    """
    Background task that periodically cleans up expired contexts.

    Runs every 10 minutes to prevent memory leaks in long-running services.
    """
    logger.info("Context Tracker background cleanup task started")

    while True:
        try:
            await asyncio.sleep(600)  # 10 minutes

            cleaned = cleanup_expired_contexts()
            if cleaned > 0:
                logger.info(f"Background cleanup removed {cleaned} expired contexts")

                # Log stats
                stats = get_store_stats()
                logger.debug(
                    f"Context store stats: {stats['active_sessions']} sessions, "
                    f"{stats['total_turns']} turns, {stats['total_entities']} entities"
                )

        except asyncio.CancelledError:
            logger.info("Context Tracker background cleanup task stopped")
            break
        except Exception as e:
            logger.error(f"Background cleanup error: {e}", exc_info=True)
            # Continue running despite errors
            await asyncio.sleep(60)  # Wait 1 minute before retry


def start_background_cleanup():
    """
    Start the background cleanup task.

    Should be called once during application startup.
    """
    global _cleanup_task

    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_background_cleanup_loop())
        logger.info("Started Context Tracker background cleanup")
    else:
        logger.warning("Background cleanup task already running")


def stop_background_cleanup():
    """
    Stop the background cleanup task.

    Should be called during application shutdown.
    """
    global _cleanup_task

    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        logger.info("Stopped Context Tracker background cleanup")

    _cleanup_task = None


# ============================================================================
# Core Context Management Functions
# ============================================================================

async def update_conversation_context(
    session_id: str,
    user_id: str,
    query: str,
    response: str,
    route: str,
    entities: List[str],
) -> None:
    """
    Update conversation context with a new turn.

    Performance requirement: <10ms for incremental updates

    Args:
        session_id: Unique session identifier
        user_id: User identifier
        query: User's query text
        response: System response text
        route: Route used for this turn
        entities: Extracted entities from query/response
    """
    now = datetime.utcnow()

    # Periodic cleanup to prevent memory leak (every ~10th call)
    # This is a fallback in addition to background task
    if hash(session_id) % 10 == 0:
        cleanup_expired_contexts()

    # Get or create context
    if session_id not in _context_store:
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            conversation_history=[],
            topic_stack=[],
            entity_mentions={},
            current_intent=None,
            context_summary=None,
            last_update_time=now,
        )
        _context_store[session_id] = context
    else:
        context = _context_store[session_id]

    # Create new turn
    turn = ConversationTurn(
        query=query,
        response=response,
        route=route,
        entities=entities,
        timestamp=now,
    )

    # Update history (keep last N turns)
    context.conversation_history.append(turn)
    if len(context.conversation_history) > CONTEXT_MAX_HISTORY_TURNS:
        context.conversation_history = context.conversation_history[-CONTEXT_MAX_HISTORY_TURNS:]

    # Update entity mentions
    for entity in entities:
        context.entity_mentions[entity] = context.entity_mentions.get(entity, 0) + 1

    # Update topic stack (simple: use route as topic indicator)
    if not context.topic_stack or context.topic_stack[-1] != route:
        context.topic_stack.append(route)
        # Keep topic stack size manageable
        if len(context.topic_stack) > 5:
            context.topic_stack = context.topic_stack[-5:]

    # Detect intent from query patterns
    context.current_intent = _detect_intent(query)

    # Update timestamp
    context.last_update_time = now

    # Trigger async summary generation if needed
    if len(context.conversation_history) >= CONTEXT_SUMMARY_MIN_TURNS:
        if len(context.conversation_history) % CONTEXT_SUMMARY_FREQUENCY == 0:
            # Fire and forget - don't block the update
            asyncio.create_task(_generate_context_summary(session_id))


def get_context_aware_routing_hints(session_id: str, query: str) -> ContextHints:
    """
    Get routing hints based on conversation context.

    Performance requirement: <5ms (synchronous, no LLM)

    Args:
        session_id: Session identifier
        query: Current query

    Returns:
        ContextHints with routing suggestions
    """
    # Default hints for new sessions
    if session_id not in _context_store:
        return ContextHints(
            resolve_references=None,
            followup=False,
            previous_route=None,
            focus_entities=[],
        )

    context = _context_store[session_id]

    # Detect if this is a follow-up question
    is_followup = _is_followup_query(query, context)

    # Get previous route
    previous_route = None
    if context.conversation_history:
        previous_route = context.conversation_history[-1].route

    # Find entities that need reference resolution
    resolve_refs = _detect_reference_pronouns(query, context)

    # Get top mentioned entities for focus
    focus_entities = _get_top_entities(context, top_k=3)

    return ContextHints(
        resolve_references=resolve_refs,
        followup=is_followup,
        previous_route=previous_route,
        focus_entities=focus_entities,
    )


def resolve_query_with_context(query: str, hints: ContextHints) -> str:
    """
    Resolve pronouns and references in query using context hints.

    Args:
        query: Original query with potential pronouns
        hints: Context hints with resolution mappings

    Returns:
        Query with pronouns resolved to entity names
    """
    if not hints.resolve_references:
        return query

    resolved = query

    # Sort by mention count (descending) to resolve most relevant first
    sorted_refs = sorted(
        hints.resolve_references.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    for entity, _ in sorted_refs:
        # Replace common Chinese pronouns (no word boundaries for Chinese)
        if '它' in resolved:
            resolved = resolved.replace('它', entity, 1)
        elif '他' in resolved:
            resolved = resolved.replace('他', entity, 1)
        elif '她' in resolved:
            resolved = resolved.replace('她', entity, 1)
        elif '这个' in resolved:
            resolved = resolved.replace('这个', entity, 1)
        elif '那个' in resolved:
            resolved = resolved.replace('那个', entity, 1)
        # Replace English pronouns (use word boundaries)
        elif re.search(r'\bit\b', resolved, flags=re.IGNORECASE):
            resolved = re.sub(r'\bit\b', entity, resolved, count=1, flags=re.IGNORECASE)
        elif re.search(r'\bthis\b', resolved, flags=re.IGNORECASE):
            resolved = re.sub(r'\bthis\b', entity, resolved, count=1, flags=re.IGNORECASE)
        elif re.search(r'\bthat\b', resolved, flags=re.IGNORECASE):
            resolved = re.sub(r'\bthat\b', entity, resolved, count=1, flags=re.IGNORECASE)

    return resolved


def cleanup_expired_contexts() -> int:
    """
    Remove expired conversation contexts based on TTL.

    Returns:
        Number of contexts cleaned up
    """
    now = datetime.utcnow()
    expiry_threshold = now - timedelta(seconds=CONTEXT_TTL_SECONDS)

    expired_sessions = [
        session_id
        for session_id, context in _context_store.items()
        if context.last_update_time < expiry_threshold
    ]

    for session_id in expired_sessions:
        del _context_store[session_id]

    if expired_sessions:
        logger.debug(f"Cleaned up {len(expired_sessions)} expired contexts")

    return len(expired_sessions)


def clear_context(session_id: str) -> bool:
    """
    Clear context for a specific session.

    Args:
        session_id: Session identifier

    Returns:
        True if context was found and cleared, False otherwise
    """
    if session_id in _context_store:
        del _context_store[session_id]
        return True
    return False


def get_context(session_id: str) -> Optional[ConversationContext]:
    """
    Get context for a specific session.

    Args:
        session_id: Session identifier

    Returns:
        ConversationContext if found, None otherwise
    """
    return _context_store.get(session_id)


# ============================================================================
# Helper Functions
# ============================================================================

def _detect_intent(query: str) -> Optional[str]:
    """Detect query intent from patterns."""
    query_lower = query.lower()

    # Relationship queries
    if any(kw in query_lower for kw in ['关系', '连接', '依赖', 'relationship', 'connection']):
        return 'relationship_query'

    # Comparison queries
    if any(kw in query_lower for kw in ['对比', '区别', '差异', 'compare', 'difference']):
        return 'comparison_query'

    # How-to queries
    if any(kw in query_lower for kw in ['如何', '怎么', '方法', 'how', 'way']):
        return 'how_to_query'

    return 'general_query'


def _is_followup_query(query: str, context: ConversationContext) -> bool:
    """Check if query is a follow-up to previous conversation."""
    if not context.conversation_history:
        return False

    # Short queries are likely follow-ups
    if len(query) < 30:
        return True

    # Check for follow-up indicators
    followup_indicators = [
        '还有', '另外', '继续', '进一步', '更多', '详细',
        'also', 'more', 'further', 'additionally', 'what about'
    ]

    query_lower = query.lower()
    return any(indicator in query_lower for indicator in followup_indicators)


def _detect_reference_pronouns(query: str, context: ConversationContext) -> Optional[Dict[str, int]]:
    """Check if query contains pronouns that need resolution."""
    pronouns = ['它', '他', '她', '这个', '那个', 'it', 'this', 'that']

    query_lower = query.lower()
    has_pronoun = any(p in query_lower for p in pronouns)

    if has_pronoun and context.entity_mentions:
        return context.entity_mentions

    return None


def _get_top_entities(context: ConversationContext, top_k: int = 3) -> List[str]:
    """Get top K most mentioned entities."""
    if not context.entity_mentions:
        return []

    sorted_entities = sorted(
        context.entity_mentions.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [entity for entity, _ in sorted_entities[:top_k]]


async def _generate_context_summary(session_id: str):
    """Generate summary of conversation context (async, non-blocking)."""
    try:
        context = _context_store.get(session_id)
        if not context or len(context.conversation_history) < CONTEXT_SUMMARY_MIN_TURNS:
            return

        # Simple summary: list recent queries
        recent_queries = [
            turn.query for turn in context.conversation_history[-5:]
        ]

        summary = f"Recent topics: {', '.join(recent_queries)}"
        context.context_summary = summary

    except Exception as e:
        logger.warning(f"Context summary generation failed for {session_id}: {e}")


# ============================================================================
# Admin/Debug Functions
# ============================================================================

def get_all_sessions() -> List[str]:
    """Get all active session IDs."""
    return list(_context_store.keys())


def get_store_stats() -> Dict[str, int]:
    """Get storage statistics."""
    total_turns = sum(
        len(ctx.conversation_history) for ctx in _context_store.values()
    )
    total_entities = sum(
        len(ctx.entity_mentions) for ctx in _context_store.values()
    )

    return {
        "active_sessions": len(_context_store),
        "total_turns": total_turns,
        "total_entities": total_entities,
    }
