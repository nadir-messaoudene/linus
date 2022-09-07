# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import json

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.osv import expression
from odoo.tools import float_is_zero, html_keep_url, is_html_empty, date_utils

class AccountMove(models.Model):
    _inherit = "account.move"

    amount_paid = fields.Float('Amount Paid', compute='compute_amount_paid', store=True)
    shopify_tag_ids = fields.Many2many('crm.tag', string="Shopify Tags (SO)")

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['shopify_tag_ids'] = self.shopify_tag_ids
        return invoice_vals

    def action_update_shopify_tag_ids(self):
        sales = self.env['sale.order'].search([('shopify_tag_ids', '!=', None)])
        for sale in sales:
            for invoice in sale.invoice_ids:
                invoice.shopify_tag_ids = sale.shopify_tag_ids