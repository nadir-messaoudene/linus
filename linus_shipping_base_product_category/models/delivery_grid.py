# -*- coding: utf-8 -*-
# Part of Syncoria. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError


class PriceRule(models.Model):
    _inherit = "delivery.price.rule"

    categ_ids = fields.Many2many('product.category', 'delivery_price_rule_category_rel', 'delivery_price_id', 'category_id', string='Product Category')
    margin = fields.Float(help='This percentage will be added to the shipping price.')
