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
from odoo.tools import float_is_zero, html_keep_url, is_html_empty


class AccountPayment(models.Model):
    _inherit = "account.payment"

    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')

    @api.onchange('sale_order_id', 'purchase_order_id')
    def onchange_so_and_po(self):
        if self.sale_order_id:
            self.ref = self.sale_order_id.name
        if self.purchase_order_id:
            self.ref = self.purchase_order_id.name

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    memo_payment = fields.One2many('account.payment', 'sale_order_id', string='Memo', copy=True)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    memo_payment = fields.One2many('account.payment', 'purchase_order_id', string='Memo', copy=True)