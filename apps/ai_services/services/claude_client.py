"""
Wrapper around the Anthropic Python SDK for Claude AI interactions.

Provides high-level methods for bill scanning, trip planning, and
expense categorisation used throughout the Tag Along application.
"""
import json
import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_client():
    """Return a configured Anthropic client."""
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _get_model():
    """Return the configured model identifier."""
    return getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')


class ClaudeService:
    """
    High-level interface to Claude for Tag Along AI features.
    """

    def __init__(self):
        self.client = _get_client()
        self.model = _get_model()

    # ------------------------------------------------------------------
    # Bill scanning
    # ------------------------------------------------------------------

    def scan_bill(self, image_base64, group_members=None):
        """
        Send a receipt/bill image to Claude and get structured item data.

        Parameters
        ----------
        image_base64 : str
            Base64-encoded image data of the receipt.
        group_members : list[dict] | None
            Optional list of group member dicts, each with at least
            ``name`` and optionally ``dietary_preference``
            (``veg``, ``non-veg``, ``vegan``, etc.).

        Returns
        -------
        dict
            Parsed receipt data with keys:
            - ``items``: list of ``{name, price, quantity, category}``
            - ``subtotal``, ``tax``, ``tip``, ``total``
            - ``currency``
            - ``suggested_splits`` (if group_members provided)
        """
        members_context = ''
        if group_members:
            members_list = '\n'.join(
                f"- {m.get('name', 'Unknown')}: {m.get('dietary_preference', 'no preference')}"
                for m in group_members
            )
            members_context = (
                f"\n\nGroup members and their dietary preferences:\n{members_list}\n\n"
                "Based on these preferences, suggest how to split the bill. "
                "Assign vegetarian items to veg members, non-veg items to non-veg members, "
                "alcohol only to members who are not marked as 'no-alcohol', "
                "and shared items (like appetizers, drinks, service charges) equally. "
                "Return a 'suggested_splits' object mapping each member's name to their suggested amount."
            )

        prompt = (
            "You are a receipt/bill parser. Analyze the provided receipt image and extract "
            "structured data.\n\n"
            "Return a JSON object with exactly these keys:\n"
            "- \"items\": array of objects, each with \"name\" (string), \"price\" (number), "
            "\"quantity\" (integer, default 1), \"category\" (one of: \"food\", \"drink\", "
            "\"alcohol\", \"dessert\", \"appetizer\", \"main\", \"side\", \"tax\", \"tip\", \"other\")\n"
            "- \"subtotal\": number\n"
            "- \"tax\": number (0 if not listed)\n"
            "- \"tip\": number (0 if not listed)\n"
            "- \"total\": number\n"
            "- \"currency\": ISO 4217 code (guess from symbols/context, default \"USD\")\n"
            "- \"restaurant_name\": string or null\n"
            "- \"date\": string in YYYY-MM-DD format or null\n"
            f"{members_context}\n\n"
            "Respond ONLY with valid JSON. No markdown, no explanation."
        )

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'image',
                                'source': {
                                    'type': 'base64',
                                    'media_type': 'image/jpeg',
                                    'data': image_base64,
                                },
                            },
                            {
                                'type': 'text',
                                'text': prompt,
                            },
                        ],
                    }
                ],
            )

            response_text = message.content[0].text.strip()

            # Strip markdown fences if present
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1]
                if response_text.endswith('```'):
                    response_text = response_text[:-3].strip()

            return json.loads(response_text)

        except json.JSONDecodeError as exc:
            logger.error('Failed to parse Claude response as JSON: %s', exc)
            raise ValueError('Could not parse the receipt. Please try a clearer image.') from exc
        except anthropic.APIError as exc:
            logger.error('Anthropic API error during bill scan: %s', exc)
            raise

    # ------------------------------------------------------------------
    # Trip planning
    # ------------------------------------------------------------------

    def plan_trip(self, description, preferences=None):
        """
        Generate a structured trip plan based on a natural-language
        description.

        Parameters
        ----------
        description : str
            Free-text description of the desired trip.
        preferences : dict | None
            Optional preferences such as ``budget``, ``duration_days``,
            ``interests``, ``group_size``, ``start_location``.

        Returns
        -------
        dict
            Trip plan with keys:
            - ``title``
            - ``summary``
            - ``duration_days``
            - ``estimated_budget``
            - ``stops``: list of ``{name, description, lat, lng,
              duration_hours, order, activities, estimated_cost}``
            - ``tips``
        """
        pref_context = ''
        if preferences:
            pref_lines = '\n'.join(
                f"- {k.replace('_', ' ').title()}: {v}"
                for k, v in preferences.items() if v
            )
            pref_context = f"\n\nPreferences:\n{pref_lines}"

        prompt = (
            "You are an expert travel planner. Based on the following trip description, "
            "create a detailed trip plan.\n\n"
            f"Description: {description}{pref_context}\n\n"
            "Return a JSON object with exactly these keys:\n"
            "- \"title\": catchy trip title (string)\n"
            "- \"summary\": 2-3 sentence overview (string)\n"
            "- \"duration_days\": integer\n"
            "- \"estimated_budget\": object with \"amount\" (number) and \"currency\" (string)\n"
            "- \"stops\": array of objects, each with:\n"
            "    - \"name\": location/place name (string)\n"
            "    - \"description\": what to do there (string)\n"
            "    - \"lat\": latitude (number or null)\n"
            "    - \"lng\": longitude (number or null)\n"
            "    - \"duration_hours\": suggested time in hours (number)\n"
            "    - \"order\": 1-indexed sequence (integer)\n"
            "    - \"activities\": array of activity strings\n"
            "    - \"estimated_cost\": object with \"amount\" (number) and \"currency\" (string)\n"
            "- \"tips\": array of useful travel tips (strings)\n\n"
            "Respond ONLY with valid JSON. No markdown, no explanation."
        )

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                    }
                ],
            )

            response_text = message.content[0].text.strip()

            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1]
                if response_text.endswith('```'):
                    response_text = response_text[:-3].strip()

            return json.loads(response_text)

        except json.JSONDecodeError as exc:
            logger.error('Failed to parse Claude trip plan response: %s', exc)
            raise ValueError('Could not generate trip plan. Please try again.') from exc
        except anthropic.APIError as exc:
            logger.error('Anthropic API error during trip planning: %s', exc)
            raise

    # ------------------------------------------------------------------
    # Expense categorisation
    # ------------------------------------------------------------------

    def categorize_expense(self, description):
        """
        Classify an expense description into one of the predefined
        category values.

        Parameters
        ----------
        description : str
            Human-readable expense description (e.g. "Uber to airport").

        Returns
        -------
        str
            One of: ``food``, ``transport``, ``accommodation``,
            ``activity``, ``shopping``, ``other``.
        """
        prompt = (
            "You are an expense categoriser. Given the following expense description, "
            "return ONLY one of these category values (lowercase, no quotes, no explanation):\n"
            "food, transport, accommodation, activity, shopping, other\n\n"
            f"Expense description: {description}"
        )

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=20,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                    }
                ],
            )

            category = message.content[0].text.strip().lower()

            valid_categories = {'food', 'transport', 'accommodation', 'activity', 'shopping', 'other'}
            if category not in valid_categories:
                logger.warning(
                    'Claude returned unexpected category "%s" for "%s", defaulting to "other".',
                    category,
                    description,
                )
                return 'other'

            return category

        except anthropic.APIError as exc:
            logger.error('Anthropic API error during categorisation: %s', exc)
            raise
