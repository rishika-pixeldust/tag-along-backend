"""
Views for the AI Services app.

Provides endpoints for bill scanning, trip planning, and automatic
expense categorisation — all powered by the Claude AI service.
"""
import base64
import logging

from rest_framework import serializers, status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Request serializers (used for validation only)
# -----------------------------------------------------------------------

class ScanBillRequestSerializer(serializers.Serializer):
    """Validates the scan-bill request payload."""
    image = serializers.ImageField(
        required=False,
        help_text='Receipt image file (multipart upload).',
    )
    image_base64 = serializers.CharField(
        required=False,
        help_text='Base64-encoded receipt image (JSON body).',
    )
    group_id = serializers.UUIDField(
        required=False,
        help_text='Optional group ID to fetch member preferences for smart splitting.',
    )

    def validate(self, attrs):
        if not attrs.get('image') and not attrs.get('image_base64'):
            raise serializers.ValidationError(
                'Provide either an "image" file or an "image_base64" string.'
            )
        return attrs


class PlanTripRequestSerializer(serializers.Serializer):
    """Validates the plan-trip request payload."""
    description = serializers.CharField(
        required=True,
        max_length=2000,
        help_text='Natural-language description of the trip.',
    )
    budget = serializers.CharField(required=False, allow_blank=True)
    duration_days = serializers.IntegerField(required=False, min_value=1)
    interests = serializers.CharField(required=False, allow_blank=True)
    group_size = serializers.IntegerField(required=False, min_value=1)
    start_location = serializers.CharField(required=False, allow_blank=True)


class CategorizeExpenseRequestSerializer(serializers.Serializer):
    """Validates the categorize-expense request payload."""
    description = serializers.CharField(
        required=True,
        max_length=500,
        help_text='Expense description to categorise.',
    )


# -----------------------------------------------------------------------
# Views
# -----------------------------------------------------------------------

class ScanBillView(APIView):
    """
    Scan a receipt/bill image and extract structured item data.

    POST /api/v1/ai/scan-bill/

    Accepts either:
    - A multipart form with an ``image`` file field, or
    - A JSON body with an ``image_base64`` string field.

    Optionally include ``group_id`` to have the AI suggest per-member
    splits based on dietary preferences.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]

    def post(self, request):
        serializer = ScanBillRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve image to base64
        if data.get('image'):
            image_bytes = data['image'].read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        else:
            image_base64 = data['image_base64']

        # Optionally resolve group members for smart splitting
        group_members = None
        group_id = data.get('group_id')
        if group_id:
            from apps.groups.models import GroupMember
            members_qs = GroupMember.objects.filter(
                group_id=group_id,
            ).select_related('user')
            group_members = [
                {
                    'name': m.user.full_name or m.user.email,
                    'dietary_preference': 'no preference',
                }
                for m in members_qs
            ]

        try:
            from apps.ai_services.services.bill_scanner import parse_receipt
            result = parse_receipt(
                image_data=image_base64,
                group_members=group_members,
            )
        except ValueError as exc:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'parsing_error',
                        'message': str(exc),
                    },
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception as exc:
            logger.error('Unexpected error in scan-bill: %s', exc)
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'internal_error',
                        'message': 'An unexpected error occurred while scanning the bill.',
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            'success': True,
            'data': result,
        })


class PlanTripView(APIView):
    """
    Generate a trip plan from a natural-language description.

    POST /api/v1/ai/plan-trip/

    Body:
    {
        "description": "3-day road trip from Mumbai to Goa",
        "budget": "500 USD",
        "duration_days": 3,
        "interests": "beaches, food, history",
        "group_size": 4,
        "start_location": "Mumbai"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PlanTripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        description = data['description']
        preferences = {
            k: v for k, v in data.items()
            if k != 'description' and v
        }

        try:
            from apps.ai_services.services.trip_planner import generate_trip_plan
            result = generate_trip_plan(
                description=description,
                preferences=preferences or None,
            )
        except ValueError as exc:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'planning_error',
                        'message': str(exc),
                    },
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception as exc:
            logger.error('Unexpected error in plan-trip: %s', exc)
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'internal_error',
                        'message': 'An unexpected error occurred while planning the trip.',
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            'success': True,
            'data': result,
        })


class CategorizeExpenseView(APIView):
    """
    Automatically categorise an expense description.

    POST /api/v1/ai/categorize-expense/

    Body: {"description": "Uber ride to the airport"}
    Response: {"success": true, "data": {"category": "transport"}}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CategorizeExpenseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        description = serializer.validated_data['description']

        try:
            from apps.ai_services.services.claude_client import ClaudeService
            claude = ClaudeService()
            category = claude.categorize_expense(description)
        except Exception as exc:
            logger.error('Unexpected error in categorize-expense: %s', exc)
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'categorization_error',
                        'message': 'Failed to categorise the expense.',
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            'success': True,
            'data': {
                'category': category,
            },
        })
