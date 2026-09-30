from odoo import _, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_wa_compose(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Enviar por WhatsApp'),
            'res_model': 'wa.compose',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_to': self.mobile or self.phone or '',
                'default_partner_id': self.id,
            },
        }
