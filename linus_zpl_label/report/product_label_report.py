# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, models, fields


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    print_format = fields.Selection(selection_add=[
        ('zpl', 'ZPL Labels (2.25 x 1.25)'),
        ('zplxprice', 'ZPL Labels with price (2.25 x 1.25)'),
        ('zpl_1_5', 'ZPL Labels (1.5 x 1.5)'),
        ('zplxprice_1_5', 'ZPL Labels with price (1.5 x 1.5)')
    ], ondelete={'zpl_1_5': 'set default', 'zplxprice_1_5': 'set default'})

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()
        if 'zpl' in self.print_format:
            data['print_format'] = self.print_format
        return xml_id, data
