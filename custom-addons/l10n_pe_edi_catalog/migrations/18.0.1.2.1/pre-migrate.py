#######################################################################################
#
#    Copyright (C) 2019-TODAY OPeru.
#    Author      :  Grupo Odoo S.A.C. (<http://www.operu.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
#######################################################################################

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    # Catalog 03: code KMT (Kilómetro) renamed to KTM
    cr.execute(
        """
        SELECT 1 FROM ir_model_data
        WHERE module = 'l10n_pe_edi_catalog' AND name = 'l10n_pe_edi_cat03_KTM'
        """
    )
    if cr.fetchone():
        _logger.info("xml_id l10n_pe_edi_catalog.l10n_pe_edi_cat03_KTM already exists, skipping")
        return
    cr.execute(
        """
        UPDATE ir_model_data
        SET name = 'l10n_pe_edi_cat03_KTM'
        WHERE module = 'l10n_pe_edi_catalog' AND name = 'l10n_pe_edi_cat03_KMT'
        RETURNING res_id
        """
    )
    row = cr.fetchone()
    if not row:
        return
    cr.execute(
        """
        UPDATE l10n_pe_edi_catalog_03
        SET code = 'KTM', complete_name = concat('KTM ', name)
        WHERE id = %s
        """,
        (row[0],),
    )
    _logger.info("Renamed l10n_pe_edi_cat03_KMT to l10n_pe_edi_cat03_KTM (id %s)", row[0])
