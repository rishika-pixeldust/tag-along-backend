"""
Currency conversion service using the open.er-api.com free API.

Rates are cached using the Django cache framework so repeated conversions
within the cache TTL avoid external HTTP calls.
"""
import logging
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache exchange rates for 1 hour (3600 seconds)
RATE_CACHE_TTL = 3600
RATE_CACHE_PREFIX = 'exchange_rate'
API_BASE_URL = 'https://open.er-api.com/v6/latest'


class CurrencyConverter:
    """
    Converts monetary amounts between currencies.

    Fetches exchange rates from the open.er-api.com free endpoint and
    caches them using the Django cache framework.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_rate(self, from_currency, to_currency):
        """
        Return the exchange rate from *from_currency* to *to_currency*.

        The rate is fetched from cache first; on a miss, it is retrieved
        from the external API and cached.

        Parameters
        ----------
        from_currency : str
            ISO 4217 source currency code (e.g. ``"USD"``).
        to_currency : str
            ISO 4217 target currency code.

        Returns
        -------
        Decimal
            The exchange rate as a ``Decimal``.

        Raises
        ------
        ValueError
            If the API does not return a rate for *to_currency*.
        ConnectionError
            If the external API is unreachable.
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return Decimal('1')

        cache_key = f'{RATE_CACHE_PREFIX}:{from_currency}:{to_currency}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Decimal(str(cached))

        # Fetch rates for the source currency
        rates = self._fetch_rates(from_currency)
        rate = rates.get(to_currency)

        if rate is None:
            raise ValueError(
                f'No exchange rate found for {from_currency} -> {to_currency}.'
            )

        rate_decimal = Decimal(str(rate))

        # Cache the fetched rate
        cache.set(cache_key, str(rate_decimal), RATE_CACHE_TTL)

        # Also cache the inverse rate
        if rate_decimal != Decimal('0'):
            inverse = (Decimal('1') / rate_decimal).quantize(
                Decimal('0.000001'), rounding=ROUND_HALF_UP
            )
            inverse_key = f'{RATE_CACHE_PREFIX}:{to_currency}:{from_currency}'
            cache.set(inverse_key, str(inverse), RATE_CACHE_TTL)

        return rate_decimal

    def convert(self, amount, from_currency, to_currency):
        """
        Convert *amount* from *from_currency* to *to_currency*.

        Parameters
        ----------
        amount : Decimal | str | int | float
            The amount to convert.
        from_currency : str
            ISO 4217 source currency code.
        to_currency : str
            ISO 4217 target currency code.

        Returns
        -------
        Decimal
            The converted amount, rounded to 2 decimal places.
        """
        amount = Decimal(str(amount))
        if from_currency.upper() == to_currency.upper():
            return amount

        rate = self.get_rate(from_currency, to_currency)
        converted = (amount * rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return converted

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_rates(self, base_currency):
        """
        Fetch all exchange rates for *base_currency* from the API.

        Returns
        -------
        dict
            ``{CURRENCY_CODE: rate}`` mapping.
        """
        url = f'{API_BASE_URL}/{base_currency.upper()}'

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error(
                'Failed to fetch exchange rates for %s: %s',
                base_currency,
                exc,
            )
            raise ConnectionError(
                f'Unable to fetch exchange rates for {base_currency}.'
            ) from exc

        data = response.json()

        if data.get('result') != 'success':
            error_type = data.get('error-type', 'unknown')
            logger.error(
                'Exchange rate API error for %s: %s',
                base_currency,
                error_type,
            )
            raise ValueError(
                f'Exchange rate API returned an error: {error_type}'
            )

        rates = data.get('rates', {})

        # Cache all rates from this base currency
        for code, rate_value in rates.items():
            cache_key = f'{RATE_CACHE_PREFIX}:{base_currency.upper()}:{code}'
            cache.set(cache_key, str(rate_value), RATE_CACHE_TTL)

        return rates
