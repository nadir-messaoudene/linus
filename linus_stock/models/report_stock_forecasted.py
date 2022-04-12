# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, models
from odoo.tools import float_is_zero, format_date, float_round

class ReplenishmentReport(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    @api.model
    def get_warehouses(self):
        return self.env['stock.location'].search_read(fields=['id', 'name', 'complete_name'])