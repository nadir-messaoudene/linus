# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


import logging
_logger = logging.getLogger(__name__)


class ShopifyFeedProducts(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'shopify.feed.products'
    _description = 'Shopify Feed Products'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.feed.products'))
    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )

    parent = fields.Boolean(default=False)
    title = fields.Char(copy=False)
    shopify_id = fields.Char(string='Shopify Id', readonly=1)
    inventory_id = fields.Char(string='Inventory Id', readonly=1)
    product_data = fields.Text(
        string='Json Data',
    )

    state = fields.Selection(
        string='state',
        selection=[('draft', 'draft'), ('queue', 'Queue'),
                   ('processed', 'Processed'), ('failed', 'Failed')]
    )

    product_id = fields.Many2one(
        string='Product Variant',
        comodel_name='product.product',
        ondelete='restrict',
    )
    product_tmpl_id = fields.Many2one(
        string='Parent Product',
        comodel_name='product.template',
        ondelete='restrict',
    )
    product_wiz_id = fields.Many2one(
        string='Product Wiz',
        comodel_name='feed.products.fetch.wizard',
        ondelete='restrict',
    )
    

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        if self.product_id and self.product_tmpl_id:
            raise UserError(_("Only one can be added"))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and self.product_tmpl_id:
            raise UserError(_("Only one can be added"))

    def update_product_product(self):
        _logger.info("update_product_product")
        if self.product_id:
            self.product_id.write({
                'shopify_id' : self.shopify_id,
                'shopify_inventory_id' : self.inventory_id,
                'marketplace_type' : 'shopify',
            })

    def update_product_template(self):
        _logger.info("update_product_template")
        if self.product_tmpl_id:
            self.product_tmpl_id.write({
                'shopify_id' : self.shopify_id,
                'shopify_inventory_id' : self.inventory_id,
                'marketplace_type' : 'shopify',
            })