# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, api, fields, tools, exceptions, _
import logging
logger = logging.getLogger(__name__)


class MarketplaceLogging(models.Model):
    _inherit = 'marketplace.logging'

    marketplace_type = fields.Selection(selection_add=[(
        'shopify', 'Shopify')], default='shopify', ondelete={'shopify': 'set default'})


class ShopifyMultiStores(models.Model):
    _name = 'shopify.multi.store'

    name = fields.Char('Name')
    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID", required=True, readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    product_tmpl_id = fields.Many2one("product.template", string="Product Template", readonly=True)
    shopify_id = fields.Char(string="Shopify Id", copy=False, required=True, readonly=True)
    shopify_parent_id = fields.Char(string="Shopify Parent Id", copy=False, readonly=True)
    shopify_inventory_id = fields.Char(string="Shopify Inventory Id", copy=False, required=True, readonly=True)

    _sql_constraints = [
        (
            'unique_shopifyinstance_byshopifyid',
            'UNIQUE(shopify_instance_id, shopify_id)',
            'Only one instance exist only one shopify id.',
        )
    ]