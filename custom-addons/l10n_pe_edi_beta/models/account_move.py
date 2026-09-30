import base64
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

from . import edi_ubl, edi_soap
from .edi_num2words import amount_to_words

_logger = logging.getLogger(__name__)

# SUNAT catalog 06 (identity doc) by length of the number
_DOC_TYPE_BY_LEN = {11: '6', 8: '1'}  # RUC / DNI
# note reason catalogs (09 credit, 10 debit); default codes
_CREDIT_CODE = '01'  # Anulación de la operación
_DEBIT_CODE = '01'   # Intereses por mora


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pe_edi_state = fields.Selection(
        [('to_send', 'Por enviar'), ('accepted', 'Aceptado'),
         ('rejected', 'Rechazado'), ('error', 'Error')],
        string='Estado SUNAT', copy=False, readonly=True)
    l10n_pe_edi_message = fields.Text('Mensaje SUNAT', copy=False, readonly=True)
    l10n_pe_edi_xml = fields.Binary('XML firmado', copy=False, readonly=True)
    l10n_pe_edi_xml_filename = fields.Char(copy=False)
    l10n_pe_edi_cdr = fields.Binary('CDR (zip)', copy=False, readonly=True)
    l10n_pe_edi_cdr_filename = fields.Char(copy=False)

    # ---- helpers -----------------------------------------------------------
    def _l10n_pe_doc_type(self):
        """SUNAT catalog 01 code: 01 factura, 03 boleta, 07 NC, 08 ND."""
        self.ensure_one()
        if self.move_type == 'out_refund':
            return '07'
        if self.move_type == 'out_invoice' and self.debit_origin_id:
            return '08'
        # factura vs boleta: RUC customer -> factura, else boleta
        vat = (self.partner_id.vat or '').strip()
        return '01' if len(vat) == 11 else '03'

    def _l10n_pe_serie_numero(self):
        self.ensure_one()
        raw = self.l10n_latam_document_number or self.name or ''
        raw = raw.replace(' ', '')
        if '-' in raw:
            serie, numero = raw.split('-', 1)
        else:
            # split leading letters+digits of serie from correlativo
            i = 0
            while i < len(raw) and not raw[i].isdigit():
                i += 1
            # serie = letter + first 3 digits (e.g. F001)
            serie, numero = raw[:i + 3], raw[i + 3:]
        return serie[:4].upper(), numero.zfill(8)

    def _l10n_pe_party(self, partner):
        vat = (partner.vat or '').strip()
        return {
            'doc_type': _DOC_TYPE_BY_LEN.get(len(vat), '1'),
            'doc_num': vat or '00000000',
            'name': partner.name or '',
            'address': {'line': partner.contact_address_inline or partner.street or ''},
        }

    def _l10n_pe_lines(self):
        out = []
        for ln in self.invoice_line_ids.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note') and l.product_id):
            qty = ln.quantity or 1.0
            base = ln.price_subtotal
            igv = ln.price_total - ln.price_subtotal
            pct = sum(ln.tax_ids.mapped('amount')) or 18.0
            out.append({
                'desc': ln.name or ln.product_id.display_name,
                'qty': qty,
                'unit_code': 'ZZ' if ln.product_id.type == 'service' else 'NIU',
                'line_ext': base,
                'igv_amount': igv,
                'unit_price_no_igv': base / qty if qty else base,
                'price_with_igv': ln.price_total / qty if qty else ln.price_total,
                'tax_pct': pct,
            })
        return out

    def _l10n_pe_build_payload(self):
        self.ensure_one()
        company = self.company_id
        doc_type = self._l10n_pe_doc_type()
        serie, numero = self._l10n_pe_serie_numero()
        cur = self.currency_id.name
        words_cur = 'SOLES' if cur == 'PEN' else 'DOLARES AMERICANOS'
        p = {
            'doc_type': doc_type,
            'serie': serie, 'numero': numero,
            'issue_date': str(self.invoice_date or fields.Date.context_today(self)),
            'issue_time': '00:00:00',
            'currency': cur,
            'supplier': {
                'ruc': (company.vat or '').strip(),
                'name': company.name,
                'address': {'line': company.partner_id.street or ''},
            },
            'customer': self._l10n_pe_party(self.partner_id),
            'lines': self._l10n_pe_lines(),
            'totals': {
                'gravada': self.amount_untaxed,
                'igv': self.amount_tax,
                'total': self.amount_total,
            },
            'tax_pct': 18,
            'legend': amount_to_words(self.amount_total, words_cur),
        }
        if doc_type in ('07', '08'):
            origin = self.reversed_entry_id or self.debit_origin_id
            if not origin:
                raise UserError(_('La nota no tiene documento de referencia.'))
            ref_serie, ref_num = origin._l10n_pe_serie_numero()
            p['ref_serie_num'] = '%s-%s' % (ref_serie, ref_num)
            p['ref_doc_type'] = origin._l10n_pe_doc_type()
            p['note_code'] = _CREDIT_CODE if doc_type == '07' else _DEBIT_CODE
            p['note_reason'] = self.ref or (_('Anulación') if doc_type == '07' else _('Nota de débito'))
        return p

    # ---- action ------------------------------------------------------------
    def action_l10n_pe_edi_send(self):
        for move in self:
            move._l10n_pe_edi_send_one()
        return True

    def _l10n_pe_edi_send_one(self):
        self.ensure_one()
        if self.state != 'posted':
            raise UserError(_('Confirma la factura antes de enviar a SUNAT.'))
        if self.country_code != 'PE':
            raise UserError(_('La empresa debe ser de Perú.'))
        company = self.company_id
        # need the signing modules available
        from . import edi_sign  # noqa: local import keeps manifest deps explicit

        try:
            payload = self._l10n_pe_build_payload()
            root = edi_ubl.build(payload)
            key_pem, cert_pem = company._l10n_pe_edi_get_keypair()
            xml_signed = edi_sign.sign_document(root, key_pem, cert_pem)
            base_name = '%s-%s-%s-%s' % (
                payload['supplier']['ruc'], payload['doc_type'],
                payload['serie'], payload['numero'])
            zip_bytes = edi_soap.zip_document(xml_signed, base_name)
            result = edi_soap.send_bill(
                zip_bytes, base_name,
                company._l10n_pe_edi_sol_username(),
                company.l10n_pe_edi_sol_pass or 'moddatos',
                production=(company.l10n_pe_edi_env == 'prod'),
            )
        except Exception as e:
            _logger.exception('SUNAT send failed for %s', self.name)
            self.write({'l10n_pe_edi_state': 'error', 'l10n_pe_edi_message': str(e)})
            return

        vals = {
            'l10n_pe_edi_xml': base64.b64encode(xml_signed),
            'l10n_pe_edi_xml_filename': base_name + '.xml',
            'l10n_pe_edi_message': '[%s] %s' % (result.get('code'), result.get('description')),
        }
        if result.get('cdr_zip'):
            vals['l10n_pe_edi_cdr'] = base64.b64encode(result['cdr_zip'])
            vals['l10n_pe_edi_cdr_filename'] = 'R-%s.zip' % base_name
        vals['l10n_pe_edi_state'] = 'accepted' if result.get('accepted') else 'rejected'
        self.write(vals)
