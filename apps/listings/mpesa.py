"""
apps/listings/mpesa.py

Thin client for Safaricom's Daraja API — just the two calls Phase 2 needs:
  1. get_access_token()  — OAuth client-credentials token (expires in ~1hr)
  2. stk_push(...)       — trigger the STK Push prompt on the buyer's phone

Kept separate from views.py so it can be unit tested independently and so
the HTTP/Daraja-specific details don't leak into the view logic.

Sandbox base URL is hardcoded for now (MPESA_ENV=sandbox). When you go live,
swap to https://api.safaricom.co.ke for production — see the `_base_url()`
function below, which already branches on MPESA_ENV so this is a one-line
change in .env, not in code.

IMPORTANT — TransactionType: Daraja's shared sandbox shortcode (174379) is
provisioned for CustomerPayBillOnline, NOT CustomerBuyGoodsOnline, regardless
of what your real business has (a Till/Buy Goods number). So while testing
against the sandbox, MPESA_TRANSACTION_TYPE must stay "CustomerPayBillOnline"
in .env. Only switch it to "CustomerBuyGoodsOnline" once you're on production
credentials for your actual Till number after Go-Live approval — mixing a
Till transaction type with the sandbox shortcode will cause STK Push to fail.
"""
import base64
import requests
from datetime import datetime
from decimal import Decimal
from django.conf import settings


class MpesaError(Exception):
    """Raised when Daraja returns an error response or the request fails."""
    pass


def _base_url():
    if settings.MPESA_ENV == 'production':
        return 'https://api.safaricom.co.ke'
    return 'https://sandbox.safaricom.co.ke'


def get_access_token():
    """
    Fetch an OAuth access token using Consumer Key/Secret (HTTP Basic Auth).
    Daraja tokens last ~3599 seconds; we don't cache it here for simplicity —
    Phase 1's traffic volume doesn't warrant it yet. If unlock volume grows,
    this is the first place to add caching (e.g. django.core.cache) to avoid
    requesting a new token on every single unlock click.
    """
    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    credentials = f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    response = requests.get(
        url,
        headers={'Authorization': f'Basic {encoded}'},
        timeout=10,
    )
    if response.status_code != 200:
        raise MpesaError(f"Failed to get access token: {response.status_code} {response.text}")

    data = response.json()
    token = data.get('access_token')
    if not token:
        raise MpesaError(f"No access_token in Daraja response: {data}")
    return token


def _generate_password(timestamp):
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    return base64.b64encode(raw.encode()).decode()


def stk_push(phone_number, amount, account_reference, transaction_desc, callback_url):
    """
    Trigger an STK Push prompt on the buyer's phone.

    phone_number: format 2547XXXXXXXX (no +, no leading 0) — e.g. 254708374149
                  for sandbox testing.
    amount: Decimal or int/float — Daraja wants a whole number, so this
            rounds up rather than truncating (never undercharge).
    account_reference: shown to the buyer on their phone, max 20 chars —
                        we use the listing's primary key.
    transaction_desc: short human-readable description, max ~100 chars.
    callback_url: full HTTPS URL Daraja will POST the result to.

    Returns the parsed JSON response, which includes CheckoutRequestID —
    the value you must persist to reconcile the async callback with this
    specific unlock attempt.
    """
    access_token = get_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = _generate_password(timestamp)

    # Daraja requires a whole-number amount; round up so we never undercharge.
    amount_int = int(Decimal(amount).to_integral_value(rounding='ROUND_CEILING'))

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": settings.MPESA_TRANSACTION_TYPE,
        "Amount": amount_int,
        "PartyA": phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": account_reference[:20],
        "TransactionDesc": transaction_desc[:100],
    }

    url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"
    response = requests.post(
        url,
        json=payload,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        timeout=15,
    )

    data = response.json()
    if response.status_code != 200 or data.get('ResponseCode') != '0':
        raise MpesaError(f"STK Push request failed: {data}")

    return data