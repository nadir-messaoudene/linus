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

    last_payment_date = fields.Date(string='Last Payment Date', compute='_compute_payments_widget_reconciled_info', store=True)

    @api.depends('move_type', 'line_ids.amount_residual')
    def _compute_payments_widget_reconciled_info(self):
        for move in self:
            payments_widget_vals = {'title': _('Less Payment'), 'outstanding': False, 'content': []}

            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                payments_widget_vals['content'] = move._get_reconciled_info_JSON_values()

            if payments_widget_vals['content']:
                move.invoice_payments_widget = json.dumps(payments_widget_vals, default=date_utils.json_default)
                last_payment_date = payments_widget_vals['content'][-1]['date']
                move.last_payment_date = last_payment_date
            else:
                move.invoice_payments_widget = json.dumps(False)
                move.last_payment_date = None

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    country_of_origin_id = fields.Many2one('res.country', string='Country of Origin')
    country_of_origin_domain = fields.Char(compute="compute_country_of_origin_domain", readonly=True, store=False)

    @api.depends('product_id')
    def compute_country_of_origin_domain(self):
        print("compute_country_of_origin_domain")
        for rec in self:
            country_of_origin_domain = json.dumps([('id', 'in', [])])
            if rec.product_id:
                if rec.product_id.product_tmpl_id.country_of_origin_ids:
                    country_of_origin_domain = json.dumps([('id', 'in', rec.product_id.product_tmpl_id.country_of_origin_ids.ids)])
                
            rec.country_of_origin_domain = country_of_origin_domain
    
    def _get_country_of_origin(self):
        self.ensure_one()
        if self.product_id and len(self.product_id.product_tmpl_id.country_of_origin_ids.ids) > 0:
            country_of_origin_id = self.product_id.product_tmpl_id.country_of_origin_ids.ids[0]
            return country_of_origin_id
        return False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountMoveLine, self)._onchange_product_id()
        for line in self:
            if line.product_id and line.product_id.product_tmpl_id.country_of_origin_ids:
                line.country_of_origin_id = self._get_country_of_origin()
        return res