from odoo import _, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_wa_send_invoice(self):
        """Open the WhatsApp composer prefilled with an invoice summary."""
        self.ensure_one()
        partner = self.partner_id
        body = _('Hola %(name)s, tu comprobante %(doc)s por %(amount)s está disponible.') % {
            'name': partner.name or '',
            'doc': self.name,
            'amount': self.currency_id.format(self.amount_total) if hasattr(self.currency_id, 'format')
            else ('%s %.2f' % (self.currency_id.name, self.amount_total)),
        }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enviar por WhatsApp'),
            'res_model': 'wa.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_to': partner.mobile or partner.phone or '',
                'default_body': body,
                'default_partner_id': partner.id,
            },
        }
