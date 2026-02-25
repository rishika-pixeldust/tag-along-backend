"""
Management command to seed realistic demo data for the Tag Along demo.

Creates users, groups, trips (with stops), and expenses so the app and
admin dashboard both show meaningful data when logged in.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --reset  # wipe existing demo data first
"""
import random
import string
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.groups.models import Group, GroupMember
from apps.trips.models import Trip, TripStop
from apps.expenses.models import Expense, ExpenseSplit

User = get_user_model()

DEMO_PASSWORD = 'TagAlong2024Demo'

DEMO_USERS = [
    {'email': 'admin@tagalong.app',      'first': 'Rishika', 'last': 'Agrawal',    'is_staff': True, 'is_superuser': True},
    {'email': 'alex.johnson@tagalong.app', 'first': 'Alex',   'last': 'Johnson',   'is_staff': False, 'is_superuser': False},
    {'email': 'priya.sharma@tagalong.app', 'first': 'Priya',  'last': 'Sharma',    'is_staff': False, 'is_superuser': False},
    {'email': 'carlos.r@tagalong.app',     'first': 'Carlos', 'last': 'Rodriguez', 'is_staff': False, 'is_superuser': False},
    {'email': 'emma.wilson@tagalong.app',  'first': 'Emma',   'last': 'Wilson',    'is_staff': False, 'is_superuser': False},
]


def _rand_code(n=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))


class Command(BaseCommand):
    help = 'Seed realistic demo data (users, groups, trips, expenses) for the Tag Along demo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing demo data before seeding',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self._reset()

        users = self._seed_users()
        groups = self._seed_groups(users)
        trips = self._seed_trips(groups, users)
        self._seed_expenses(groups, trips, users)

        self.stdout.write(self.style.SUCCESS('\n✅ Demo data seeded successfully!\n'))
        self.stdout.write(f'Users created:    {len(users)}')
        self.stdout.write(f'Groups created:   {len(groups)}')
        self.stdout.write(f'Trips created:    {len(trips)}')
        self.stdout.write('\nDemo login credentials:')
        for u in DEMO_USERS:
            self.stdout.write(f'  {u["email"]} / {DEMO_PASSWORD}')

    # -----------------------------------------------------------------------

    def _reset(self):
        self.stdout.write('Resetting demo data...')
        emails = [u['email'] for u in DEMO_USERS]
        demo_users = User.objects.filter(email__in=emails)
        Expense.objects.filter(paid_by__in=demo_users).delete()
        Trip.objects.filter(created_by__in=demo_users).delete()
        Group.objects.filter(created_by__in=demo_users).delete()
        demo_users.delete()
        self.stdout.write('  Reset complete.')

    def _seed_users(self):
        self.stdout.write('\nSeeding users...')
        users = {}
        for data in DEMO_USERS:
            email = data['email']
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0].replace('.', '_'),
                    'first_name': data['first'],
                    'last_name': data['last'],
                    'is_staff': data['is_staff'],
                    'is_superuser': data['is_superuser'],
                    'is_active': True,
                },
            )
            user.set_password(DEMO_PASSWORD)
            if not created:
                user.first_name = data['first']
                user.last_name = data['last']
                user.is_staff = data['is_staff']
                user.is_superuser = data['is_superuser']
            user.save()
            users[email] = user
            status = 'created' if created else 'updated'
            self.stdout.write(f'  {status}: {email}')
        return users

    def _seed_groups(self, users):
        self.stdout.write('\nSeeding groups...')
        admin = users['admin@tagalong.app']
        alex = users['alex.johnson@tagalong.app']
        priya = users['priya.sharma@tagalong.app']
        carlos = users['carlos.r@tagalong.app']
        emma = users['emma.wilson@tagalong.app']

        groups = {}

        # Group 1: Europe Summer 2024
        g1, _ = Group.objects.get_or_create(
            name='Europe Summer 2024',
            created_by=admin,
            defaults={
                'description': 'Our epic summer trip across Paris, Amsterdam, and Switzerland!',
                'invite_code': _rand_code(),
                'is_active': True,
            },
        )
        self._add_members(g1, admin=admin, members=[alex, priya, carlos, emma])
        groups['europe'] = g1
        self.stdout.write(f'  created/updated group: {g1.name}')

        # Group 2: Goa Beach Trip
        g2, _ = Group.objects.get_or_create(
            name='Goa Beach Trip',
            created_by=admin,
            defaults={
                'description': 'New Year vibes at the beach 🏖️',
                'invite_code': _rand_code(),
                'is_active': True,
            },
        )
        self._add_members(g2, admin=admin, members=[priya, carlos])
        groups['goa'] = g2
        self.stdout.write(f'  created/updated group: {g2.name}')

        return groups

    def _add_members(self, group, admin, members):
        """Ensure admin is group admin and all members are in the group."""
        GroupMember.objects.get_or_create(group=group, user=admin, defaults={'role': 'admin'})
        for user in members:
            GroupMember.objects.get_or_create(group=group, user=user, defaults={'role': 'member'})

    def _seed_trips(self, groups, users):
        self.stdout.write('\nSeeding trips...')
        admin = users['admin@tagalong.app']
        europe = groups['europe']
        goa = groups['goa']
        trips = {}

        # Trip 1: Paris & Amsterdam — completed
        t1, _ = Trip.objects.get_or_create(
            name='Paris & Amsterdam Highlights',
            group=europe,
            defaults={
                'description': 'Art, canals, croissants, and unforgettable memories.',
                'start_date': date(2024, 6, 15),
                'end_date': date(2024, 6, 25),
                'status': 'completed',
                'start_location_name': 'Charles de Gaulle Airport, Paris',
                'start_lat': '49.0097',
                'start_lng': '2.5479',
                'end_location_name': 'Amsterdam Schiphol Airport',
                'end_lat': '52.3105',
                'end_lng': '4.7683',
                'created_by': admin,
            },
        )
        self._seed_stops(t1, admin, [
            ('Eiffel Tower', 'Champ de Mars, Paris', '48.8584', '2.2945', 0),
            ('Louvre Museum', 'Rue de Rivoli, Paris', '48.8606', '2.3376', 1),
            ('Amsterdam Dam Square', 'Dam, Amsterdam', '52.3731', '4.8932', 2),
            ('Anne Frank House', 'Prinsengracht 263, Amsterdam', '52.3752', '4.8840', 3),
        ])
        trips['paris'] = t1
        self.stdout.write(f'  created/updated trip: {t1.name}')

        # Trip 2: Swiss Alps Skiing — planning
        t2, _ = Trip.objects.get_or_create(
            name='Swiss Alps Christmas',
            group=europe,
            defaults={
                'description': 'Skiing, fondue, and Alpine magic for Christmas!',
                'start_date': date(2024, 12, 20),
                'end_date': date(2024, 12, 28),
                'status': 'planning',
                'start_location_name': 'Zurich Airport',
                'start_lat': '47.4582',
                'start_lng': '8.5555',
                'end_location_name': 'Zermatt, Switzerland',
                'end_lat': '46.0207',
                'end_lng': '7.7491',
                'created_by': admin,
            },
        )
        self._seed_stops(t2, admin, [
            ('Zurich Old Town', 'Altstadt, Zurich', '47.3769', '8.5417', 0),
            ('Interlaken', 'Interlaken, Switzerland', '46.6863', '7.8632', 1),
            ('Zermatt & Matterhorn', 'Zermatt, Switzerland', '46.0207', '7.7491', 2),
        ])
        trips['swiss'] = t2
        self.stdout.write(f'  created/updated trip: {t2.name}')

        # Trip 3: Goa New Year — active
        t3, _ = Trip.objects.get_or_create(
            name='Goa New Year 2025',
            group=goa,
            defaults={
                'description': 'Ringing in 2025 with beach parties and seafood feasts 🎆',
                'start_date': date(2024, 12, 31),
                'end_date': date(2025, 1, 5),
                'status': 'active',
                'start_location_name': 'Goa International Airport',
                'start_lat': '15.3809',
                'start_lng': '73.8314',
                'end_location_name': 'Calangute Beach, North Goa',
                'end_lat': '15.5440',
                'end_lng': '73.7523',
                'created_by': admin,
            },
        )
        self._seed_stops(t3, admin, [
            ('Calangute Beach', 'Calangute, North Goa', '15.5440', '73.7523', 0),
            ('Anjuna Flea Market', 'Anjuna, North Goa', '15.5735', '73.7404', 1),
            ('Old Goa Churches', 'Old Goa', '15.5009', '73.9115', 2),
        ])
        trips['goa'] = t3
        self.stdout.write(f'  created/updated trip: {t3.name}')

        return trips

    def _seed_stops(self, trip, user, stops):
        for name, desc, lat, lng, order in stops:
            TripStop.objects.get_or_create(
                trip=trip,
                name=name,
                defaults={
                    'description': desc,
                    'lat': lat,
                    'lng': lng,
                    'order': order,
                    'added_by': user,
                },
            )

    def _seed_expenses(self, groups, trips, users):
        self.stdout.write('\nSeeding expenses...')
        admin = users['admin@tagalong.app']
        alex = users['alex.johnson@tagalong.app']
        priya = users['priya.sharma@tagalong.app']
        carlos = users['carlos.r@tagalong.app']
        emma = users['emma.wilson@tagalong.app']
        europe = groups['europe']
        goa = groups['goa']
        paris_trip = trips['paris']
        goa_trip = trips['goa']

        europe_members = [admin, alex, priya, carlos, emma]
        goa_members = [admin, priya, carlos]

        expenses_data = [
            # Europe / Paris trip
            ('Airbnb Paris — 3 nights', 450.00, 'accommodation', admin, europe, paris_trip, date(2024, 6, 15), europe_members),
            ('CDG Airport Transfer', 85.00, 'transport', alex, europe, paris_trip, date(2024, 6, 15), europe_members),
            ('Louvre Museum Tickets', 120.00, 'activity', priya, europe, paris_trip, date(2024, 6, 17), europe_members),
            ('Dinner at Le Jules Verne', 320.00, 'food', admin, europe, paris_trip, date(2024, 6, 18), europe_members),
            ('Amsterdam Canal Cruise', 95.00, 'activity', carlos, europe, paris_trip, date(2024, 6, 21), europe_members),
            ('Hotel Amstel Amsterdam', 380.00, 'accommodation', emma, europe, paris_trip, date(2024, 6, 21), europe_members),
            ('Thalys Train Paris → Amsterdam', 165.00, 'transport', alex, europe, paris_trip, date(2024, 6, 20), europe_members),
            # Goa trip
            ('Beach Shack Dinner', 75.00, 'food', admin, goa, goa_trip, date(2024, 12, 31), goa_members),
            ('Scooter Rental — 3 days', 45.00, 'transport', priya, goa, goa_trip, date(2025, 1, 1), goa_members),
            ('Beach Yoga Session', 30.00, 'activity', carlos, goa, goa_trip, date(2025, 1, 2), goa_members),
        ]

        for description, amount, category, paid_by, group, trip, exp_date, members in expenses_data:
            expense, created = Expense.objects.get_or_create(
                description=description,
                group=group,
                paid_by=paid_by,
                defaults={
                    'amount': amount,
                    'currency': 'USD',
                    'category': category,
                    'split_type': 'equal',
                    'trip': trip,
                    'date': exp_date,
                },
            )
            if created:
                # Create equal splits
                split_amount = round(amount / len(members), 2)
                for member in members:
                    ExpenseSplit.objects.get_or_create(
                        expense=expense,
                        user=member,
                        defaults={'amount': split_amount},
                    )
            self.stdout.write(f'  {"created" if created else "exists"}: {description} (${amount})')
