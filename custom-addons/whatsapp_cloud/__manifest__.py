{
    'name': "WhatsApp Cloud API",
    'summary': "Enviar mensajes de WhatsApp desde Odoo vía Meta Cloud API (Graph).",
    'description': """
Integración ligera con la WhatsApp Business Cloud API de Meta (sin Enterprise):

* Configuración en la empresa: Phone Number ID, token y versión de API.
* Envío de texto libre y de plantillas (templates) aprobadas.
* Asistente para redactar y enviar a un contacto.
* Botón en facturas de cliente para notificar al cliente por WhatsApp.

Nota: el texto libre solo entrega dentro de la ventana de 24h de servicio; fuera de
ella Meta exige una plantilla aprobada. Requiere una cuenta de WhatsApp Business y un
token con permiso whatsapp_business_messaging.
    """,
    'version': '18.0.1.0.0',
    'author': "Claude",
    'category': 'Marketing',
    'license': 'LGPL-3',
    'depends': ['account', 'mail', 'contacts'],
    'external_dependencies': {'python': ['requests']},
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/account_move_views.xml',
        'wizard/wa_compose_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
}
