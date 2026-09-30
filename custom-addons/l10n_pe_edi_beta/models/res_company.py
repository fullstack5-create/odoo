from odoo import fields, models
from . import edi_sign


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pe_edi_env = fields.Selection(
        [('beta', 'Beta (pruebas)'), ('prod', 'Producción')],
        string='Ambiente SUNAT', default='beta')
    l10n_pe_edi_sol_user = fields.Char('Usuario SOL', default='MODDATOS')
    l10n_pe_edi_sol_pass = fields.Char('Clave SOL', default='moddatos')
    l10n_pe_edi_cert = fields.Binary('Certificado (.pfx/.p12)')
    l10n_pe_edi_cert_filename = fields.Char('Nombre certificado')
    l10n_pe_edi_cert_pass = fields.Char('Clave certificado')

    def _l10n_pe_edi_get_keypair(self):
        """Return (key_pem, cert_pem). Beta without cert -> self-signed."""
        self.ensure_one()
        if self.l10n_pe_edi_cert:
            import base64
            pfx = base64.b64decode(self.l10n_pe_edi_cert)
            return edi_sign.load_cert(pfx, self.l10n_pe_edi_cert_pass or '')
        # Beta fallback: generate a throwaway self-signed certificate
        return edi_sign.generate_self_signed(self.vat or '20000000001')

    def _l10n_pe_edi_sol_username(self):
        self.ensure_one()
        return '%s%s' % (self.vat or '', self.l10n_pe_edi_sol_user or 'MODDATOS')
