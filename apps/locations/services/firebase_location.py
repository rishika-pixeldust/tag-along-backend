"""
Firebase Firestore service for real-time location data.

Reads and writes user location documents from the ``locations`` collection
in Firestore.  Each document is keyed by user ID and contains the latest
lat/lng, timestamp, and optional metadata.
"""
import logging
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import firestore

logger = logging.getLogger(__name__)

# Firestore collection name for location data
LOCATIONS_COLLECTION = 'locations'


def _get_firestore_client():
    """
    Return a Firestore client, initialising the default Firebase app
    if it hasn't been initialised yet.
    """
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    return firestore.client()


class FirebaseLocationService:
    """
    Service for reading / writing user location data in Firestore.
    """

    def __init__(self):
        self.db = _get_firestore_client()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_group_member_locations(self, group_id, member_ids):
        """
        Retrieve the latest locations for a list of group members.

        Each member's location document is stored at
        ``locations/{user_id}`` and may contain sub-collections or
        fields scoped by group.  This method reads the top-level
        document for each member and returns their most recent
        coordinates.

        Parameters
        ----------
        group_id : str
            The UUID of the group (used for logging / filtering).
        member_ids : list[str]
            User ID strings whose locations should be fetched.

        Returns
        -------
        list[dict]
            A list of dictionaries, each containing:
            ``user_id``, ``latitude``, ``longitude``, ``timestamp``,
            and an optional ``accuracy`` field.
        """
        locations = []

        for member_id in member_ids:
            try:
                doc_ref = self.db.collection(LOCATIONS_COLLECTION).document(member_id)
                doc = doc_ref.get()

                if not doc.exists:
                    logger.debug(
                        'No location document for user %s in group %s',
                        member_id,
                        group_id,
                    )
                    continue

                data = doc.to_dict()
                location_entry = {
                    'user_id': member_id,
                    'latitude': data.get('latitude'),
                    'longitude': data.get('longitude'),
                    'timestamp': data.get('timestamp'),
                    'accuracy': data.get('accuracy'),
                }

                # Only include entries that have valid coordinates
                if location_entry['latitude'] is not None and location_entry['longitude'] is not None:
                    locations.append(location_entry)

            except Exception as exc:
                logger.warning(
                    'Error fetching location for user %s: %s',
                    member_id,
                    exc,
                )
                continue

        return locations

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def update_location(self, user_id, location_data):
        """
        Write or update a user's location document in Firestore.

        Parameters
        ----------
        user_id : str
            The UUID of the user.
        location_data : dict
            Must contain ``latitude`` and ``longitude``.  May also
            include ``accuracy``, ``altitude``, ``speed``, ``heading``.

        Returns
        -------
        bool
            ``True`` if the write succeeded.

        Raises
        ------
        ValueError
            If required fields are missing.
        """
        if 'latitude' not in location_data or 'longitude' not in location_data:
            raise ValueError('location_data must contain latitude and longitude.')

        doc_ref = self.db.collection(LOCATIONS_COLLECTION).document(str(user_id))

        payload = {
            'latitude': location_data['latitude'],
            'longitude': location_data['longitude'],
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'accuracy': location_data.get('accuracy'),
            'altitude': location_data.get('altitude'),
            'speed': location_data.get('speed'),
            'heading': location_data.get('heading'),
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        try:
            doc_ref.set(payload, merge=True)
            logger.info('Updated location for user %s', user_id)
            return True
        except Exception as exc:
            logger.error(
                'Failed to update location for user %s: %s',
                user_id,
                exc,
            )
            raise
