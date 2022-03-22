# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


import logging
_logger = logging.getLogger(__name__)


class ShopifyFeedOrders(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'shopify.feed.orders'
    _description = 'Shopify Feed Orders'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.feed.orders'))
    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    shopify_id = fields.Char(string='Shopify Id', readonly=1)
    order_data = fields.Text(readonly=1)
    state = fields.Selection(
        string='state',
        selection=[('draft', 'draft'), 
                    ('queue', 'Queue'),
                   ('processed', 'Processed'), 
                   ('failed', 'Failed')]
    )
    order_wiz_id = fields.Many2one(
        string='Order Wiz',
        comodel_name='feed.order.fetch.wizard',
        ondelete='restrict',
    )