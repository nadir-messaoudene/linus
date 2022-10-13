# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from functools import partial
from itertools import count, groupby
import json

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.osv import expression
from odoo.tools import float_is_zero, html_keep_url, is_html_empty


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    delivery_status = fields.Selection([
        ('none', ''),
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('push_3pl', 'Pushed to 3PL'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
        ], string='Delivery Status', default='none', compute='_action_get_delivery', store=True)
    count_backorder = fields.Integer('Back Orders Count', compute='_action_get_delivery', store=True)

    @api.depends('picking_ids.state')
    def _action_get_delivery(self):
        for order in self:
            pickings = order.picking_ids.filtered(lambda l: l.picking_type_id.code != 'internal').sorted(lambda p: p.id)
            backorders = pickings.backorder_ids.filtered(lambda l: l.state not in ('done', 'cancel'))
            order.count_backorder = len(backorders)

            if len(pickings) > 0:
                order.delivery_status = pickings[-1].state
            else:
                order.delivery_status = 'none'
