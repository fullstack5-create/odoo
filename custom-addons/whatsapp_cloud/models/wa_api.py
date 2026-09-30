"""Pure helpers for the Meta WhatsApp Cloud API (Graph). No Odoo imports."""
import re

import requests

GRAPH = 'https://graph.facebook.com'


def normalize_msisdn(raw, default_cc='51'):
    """Return digits-only phone in international format (no '+').

    Naive: strips non-digits; a 9-digit number (Peru mobile) gets the default
    country code. ponytail: good enough; use a phonenumbers lib if you need
    real multi-country parsing.
    """
    digits = re.sub(r'\D', '', raw or '')
    if len(digits) == 9 and default_cc:
        digits = default_cc + digits
    return digits


def text_payload(to, body):
    return {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': to,
        'type': 'text',
        'text': {'preview_url': False, 'body': body},
    }


def template_payload(to, name, lang_code, components=None):
    template = {'name': name, 'language': {'code': lang_code}}
    if components:
        template['components'] = components
    return {
        'messaging_product': 'whatsapp',
        'to': to,
        'type': 'template',
        'template': template,
    }


def send(api_version, phone_number_id, token, payload, timeout=30):
    """POST to the messages endpoint. Returns (ok, message_id_or_error)."""
    url = '%s/%s/%s/messages' % (GRAPH, api_version, phone_number_id)
    resp = requests.post(
        url, json=payload,
        headers={'Authorization': 'Bearer %s' % token},
        timeout=timeout,
    )
    data = resp.json() if resp.content else {}
    if resp.ok and data.get('messages'):
        return True, data['messages'][0].get('id', '')
    err = data.get('error', {})
    return False, err.get('message') or ('HTTP %s' % resp.status_code)
