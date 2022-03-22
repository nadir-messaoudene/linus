# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


import logging
_logger = logging.getLogger(__name__)


class ShopifyFeedCustomers(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'shopify.feed.customers'
    _description = 'Shopify Feed Customers'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.feed.customers'))
    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    shopify_id = fields.Char(string='Shopify Id', readonly=1)
    customer_data = fields.Text(
        string='Customer Data',
    )
    state = fields.Selection(
        string='state',
        selection=[('draft', 'draft'), ('queue', 'Queue'),
                   ('processed', 'Processed'), ('failed', 'Failed')]
    )
    customer_wiz_id = fields.Many2one(
        string='Customer Wiz',
        comodel_name='feed.customers.fetch.wizard',
        ondelete='restrict',
    )