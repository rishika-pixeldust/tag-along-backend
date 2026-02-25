"""
Custom exception handler for Django REST Framework.
"""
import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    ValidationError as DRFValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent JSON error responses.

    Response format:
    {
        "success": false,
        "error": {
            "code": "error_code",
            "message": "Human-readable message",
            "details": { ... }  // optional, for field-level validation errors
        }
    }
    """
    # Convert Django ValidationError to DRF ValidationError
    if isinstance(exc, DjangoValidationError):
        exc = DRFValidationError(detail=exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)

    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception
        logger.exception(
            'Unhandled exception in %s',
            context.get('view', 'unknown view'),
            exc_info=exc,
        )
        return Response(
            {
                'success': False,
                'error': {
                    'code': 'internal_error',
                    'message': 'An unexpected error occurred. Please try again later.',
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Build structured error response
    error_response = {
        'success': False,
        'error': _format_error(exc, response),
    }

    response.data = error_response
    return response


def _format_error(exc, response):
    """Format the error payload based on exception type."""
    if isinstance(exc, DRFValidationError):
        return {
            'code': 'validation_error',
            'message': 'Invalid input.',
            'details': response.data,
        }

    if isinstance(exc, Http404):
        return {
            'code': 'not_found',
            'message': 'The requested resource was not found.',
        }

    if isinstance(exc, APIException):
        return {
            'code': exc.default_code if hasattr(exc, 'default_code') else 'error',
            'message': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
        }

    return {
        'code': 'error',
        'message': 'An error occurred.',
    }
