"""
Orchestrates the bill/receipt scanning flow.

Takes raw image data, optionally resolves group members, invokes the
Claude service, and returns a structured result.
"""
import base64
import logging

from apps.ai_services.services.claude_client import ClaudeService

logger = logging.getLogger(__name__)


def parse_receipt(image_data, group_members=None):
    """
    Parse a receipt image and return structured item/split data.

    Parameters
    ----------
    image_data : str | bytes
        Either a base64-encoded string or raw image bytes.
    group_members : list[dict] | None
        Optional list of member dicts with ``name`` and
        ``dietary_preference`` keys.  When provided, the service will
        also suggest per-member splits.

    Returns
    -------
    dict
        Parsed receipt data including ``items``, ``total``, ``currency``,
        and (when members are supplied) ``suggested_splits``.

    Raises
    ------
    ValueError
        If the image cannot be processed or the AI response is unusable.
    """
    # Ensure we have a base64 string
    if isinstance(image_data, bytes):
        image_base64 = base64.b64encode(image_data).decode('utf-8')
    elif isinstance(image_data, str):
        # If it already looks like base64, use as-is;
        # otherwise assume it's raw bytes that were decoded to str incorrectly.
        image_base64 = image_data
    else:
        raise ValueError('image_data must be bytes or a base64-encoded string.')

    claude = ClaudeService()

    try:
        result = claude.scan_bill(
            image_base64=image_base64,
            group_members=group_members,
        )
    except Exception as exc:
        logger.error('Bill scanning failed: %s', exc)
        raise ValueError(
            'Failed to parse the receipt. Please try again with a clearer image.'
        ) from exc

    # Basic validation of the response
    if not isinstance(result, dict):
        raise ValueError('Unexpected response format from AI service.')

    if 'items' not in result:
        result['items'] = []
    if 'total' not in result:
        result['total'] = sum(
            item.get('price', 0) * item.get('quantity', 1)
            for item in result['items']
        )

    return result
