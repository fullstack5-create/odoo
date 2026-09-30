from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError
from odoo.addons.whatsapp_cloud.models import wa_api


@tagged('post_install', '-at_install')
class TestWhatsApp(TransactionCase):

    def test_normalize(self):
        self.assertEqual(wa_api.normalize_msisdn('+51 987 654 321'), '51987654321')
        self.assertEqual(wa_api.normalize_msisdn('987654321'), '51987654321')  # PE 9-digit
        self.assertEqual(wa_api.normalize_msisdn('51987654321'), '51987654321')

    def test_payloads(self):
        t = wa_api.text_payload('51987654321', 'hola')
        self.assertEqual(t['type'], 'text')
        self.assertEqual(t['text']['body'], 'hola')
        tpl = wa_api.template_payload('51987654321', 'saludo', 'es')
        self.assertEqual(tpl['template']['name'], 'saludo')
        self.assertEqual(tpl['template']['language']['code'], 'es')

    def test_send_requires_config(self):
        self.env.company.write({'wa_phone_number_id': False, 'wa_access_token': False})
        with self.assertRaises(UserError):
            self.env.company.wa_send_text('51987654321', 'hola')
