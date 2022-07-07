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


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_status = fields.Selection([
        ('none', ''),
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('push_3pl', 'Pushed to 3PL'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
        ], string='Delivery Status', default='none', compute='_get_delivery_status', store=True)

    last_carrier_tracking_ref = fields.Char(string='Tracking Reference',compute='_get_delivery_status', store=True)

    @api.depends('picking_ids.state')
    def _get_delivery_status(self):
        for order in self:
            if len(order.picking_ids) > 0:
                order.delivery_status = order.picking_ids.sorted()[-1].state
                order.last_carrier_tracking_ref = order.picking_ids.sorted()[-1].carrier_tracking_ref
            else: 
                order.delivery_status = 'none'
                order.last_carrier_tracking_ref = ''

    def action_update(self):
        to_update = self.env['sale.order'].search([])
        if not to_update:
            return
        for rec in to_update:
            rec._get_delivery_status()
    