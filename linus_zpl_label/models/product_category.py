# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    zpl_label_format = fields.Selection([('accessory', 'Accessory'), ('bicycle', 'Bicycle')], string="ZPL Label Format")
