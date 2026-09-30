from odoo import _, fields, models


class WaCompose(models.TransientModel):
    _name = 'wa.compose'
    _description = 'Redactar mensaje de WhatsApp'

    to = fields.Char('Número (con código país)', required=True)
    body = fields.Text('Mensaje', required=True)
    partner_id = fields.Many2one('res.partner', 'Contacto')

    def action_send(self):
        self.ensure_one()
        msg_id = self.env.company.wa_send_text(self.to, self.body)
        if self.partner_id:
            self.partner_id.message_post(
                body=_('WhatsApp enviado (id %(id)s): %(body)s',
                       id=msg_id, body=self.body))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('WhatsApp enviado (id %s).') % msg_id,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
