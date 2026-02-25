"""
Trip planning service that wraps the Claude AI call and
returns a structured trip plan.
"""
import logging

from apps.ai_services.services.claude_client import ClaudeService

logger = logging.getLogger(__name__)


def generate_trip_plan(description, preferences=None):
    """
    Generate a structured trip plan from a natural-language description.

    Parameters
    ----------
    description : str
        Free-text description of the desired trip (e.g.
        "3-day road trip from SF to LA along the coast").
    preferences : dict | None
        Optional dict of user preferences.  Recognised keys include
        ``budget``, ``duration_days``, ``interests``, ``group_size``,
        ``start_location``.

    Returns
    -------
    dict
        A structured trip plan containing ``title``, ``summary``,
        ``duration_days``, ``estimated_budget``, ``stops`` (list),
        and ``tips``.

    Raises
    ------
    ValueError
        If the AI service returns an unusable response.
    """
    if not description or not description.strip():
        raise ValueError('Trip description must not be empty.')

    claude = ClaudeService()

    try:
        result = claude.plan_trip(
            description=description.strip(),
            preferences=preferences,
        )
    except Exception as exc:
        logger.error('Trip planning failed: %s', exc)
        raise ValueError(
            'Failed to generate a trip plan. Please try again.'
        ) from exc

    # Basic validation
    if not isinstance(result, dict):
        raise ValueError('Unexpected response format from AI service.')

    # Ensure required fields exist with sensible defaults
    result.setdefault('title', 'Untitled Trip')
    result.setdefault('summary', '')
    result.setdefault('duration_days', 1)
    result.setdefault('stops', [])
    result.setdefault('tips', [])

    return result
