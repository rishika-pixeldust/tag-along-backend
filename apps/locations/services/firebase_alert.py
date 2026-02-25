"""
Firebase service for delivering route deviation alerts via
Firestore (real-time) and FCM push notifications (background).
"""
import logging

from firebase_admin import firestore, messaging

logger = logging.getLogger(__name__)


class FirebaseAlertService:
    """Handles delivery of route-deviation alerts through Firebase."""

    def __init__(self):
        self.db = firestore.client()

    def send_alert_notification(
        self,
        alert_id: str,
        recipient_id: str,
        sender_id: str,
        sender_name: str,
        message: str,
        group_id: str,
        trip_id: str,
    ) -> None:
        """
        Write a notification document to Firestore for real-time delivery.

        Path: notifications/{recipientId}/items/{alertId}
        """
        doc_ref = (
            self.db.collection('notifications')
            .document(recipient_id)
            .collection('items')
            .document(alert_id)
        )
        doc_ref.set({
            'id': alert_id,
            'type': 'route_alert',
            'senderId': sender_id,
            'senderName': sender_name,
            'message': message,
            'groupId': group_id,
            'tripId': trip_id,
            'read': False,
            'playedAudio': False,
            'createdAt': firestore.SERVER_TIMESTAMP,
        })
        logger.info(
            'Route alert %s written to Firestore for recipient %s',
            alert_id,
            recipient_id,
        )

    def send_fcm_push(
        self,
        recipient_fcm_token: str | None,
        sender_name: str,
        message: str,
    ) -> None:
        """
        Send an FCM push notification as backup delivery for when the
        app is backgrounded or terminated.
        """
        if not recipient_fcm_token:
            logger.warning('No FCM token for recipient, skipping push.')
            return

        try:
            fcm_message = messaging.Message(
                notification=messaging.Notification(
                    title=f'Route Alert from {sender_name}',
                    body=message,
                ),
                data={
                    'type': 'route_alert',
                    'message': message,
                    'senderName': sender_name,
                },
                token=recipient_fcm_token,
            )
            messaging.send(fcm_message)
            logger.info('FCM push sent to token %s...', recipient_fcm_token[:20])
        except Exception as exc:
            logger.error('Failed to send FCM push: %s', exc)
