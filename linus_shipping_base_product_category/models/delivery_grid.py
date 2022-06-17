# -*- coding: utf-8 -*-
# Part of Syncoria. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class PriceRule(models.Model):
    _inherit = "delivery.price.rule"

    categ_ids = fields.Many2many('product.category', 'delivery_price_rule_category_rel', 'delivery_price_id', 'category_id', string='Product Category')
    description = fields.Char()
