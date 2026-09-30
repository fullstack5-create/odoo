from odoo import _, fields, models
from odoo.exceptions import UserError

from . import wa_api


class ResCompany(models.Model):
    _inherit = 'res.company'

    wa_phone_number_id = fields.Char('WhatsApp Phone Number ID')
    wa_access_token = fields.Char('WhatsApp Access Token')
    wa_api_version = fields.Char('WhatsApp API Version', default='v21.0')

    def _wa_check_config(self):
        self.ensure_one()
        if not (self.wa_phone_number_id and self.wa_access_token):
            raise UserError(_('Configura Phone Number ID y Access Token de WhatsApp en la empresa.'))

    def _wa_send(self, payload):
        """Send a prebuilt payload. Returns message id; raises on failure."""
        self._wa_check_config()
        ok, result = wa_api.send(
            self.wa_api_version or 'v21.0',
            self.wa_phone_number_id, self.wa_access_token, payload)
        if not ok:
            raise UserError(_('WhatsApp rechazó el mensaje: %s') % result)
        return result

    def wa_send_text(self, to, body):
        to = wa_api.normalize_msisdn(to)
        if not to:
            raise UserError(_('Número de WhatsApp inválido.'))
        return self._wa_send(wa_api.text_payload(to, body))

    def wa_send_template(self, to, name, lang_code='es', components=None):
        to = wa_api.normalize_msisdn(to)
        if not to:
            raise UserError(_('Número de WhatsApp inválido.'))
        return self._wa_send(wa_api.template_payload(to, name, lang_code, components))
