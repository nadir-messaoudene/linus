# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
from dataclasses import field

from odoo import models, fields, exceptions, api, _
import logging

_logger = logging.getLogger(__name__)


class ShopifyFulfilment(models.Model):
    _name = "shopify.fulfilment"
    _rec_name = "name"

    shopify_created_at = fields.Char(string='Created At')
    shopify_fulfilment_id = fields.Char(string='Shopify Fulfilment Id', readonly=1)

    name = fields.Char(string="Fulfilment")

    sale_order_id = fields.Many2one(
        string='Order',
        comodel_name='sale.order',
        ondelete='restrict',
    )
    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    shopify_order_id = fields.Char(string='Shopify Order ID', readonly=1)
    shopify_fulfilment_tracking_number = fields.Char(string='Tracking Number', readonly=1)
    shopify_fulfilment_service = fields.Char(string='Service', readonly=1)
    shopify_fulfilment_line = fields.One2many(
        comodel_name='shopify.fulfilment.line',
        inverse_name='shopify_fulfilment_id',
        string='Shopify Fulfilment Line',
        required=False)
    shopify_status = fields.Char(
        string='Status',
        required=False)

    shopify_fulfilment_status = fields.Char(
        string='Fulfilment Status',
        required=False)


class ShopifyFulfilmentLine(models.Model):
    _name = "shopify.fulfilment.line"


    shopify_fulfilment_id = fields.Many2one(
        comodel_name='shopify.fulfilment',
        string='Shopify Fulfilment',
        required=False,invisible=1,ondelete='cascade')

    sale_order_id = fields.Many2one(
        string='Order',
        comodel_name='sale.order',
        ondelete='restrict',
    )
    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    shopify_created_at = fields.Char(string='Created At')

    name = fields.Char(string="Fulfilment")

    shopify_fulfilment_line_id = fields.Char(string='Line Id', readonly=1)
    shopify_fulfilment_product_id = fields.Char(string=' Product Id', readonly=1)
    shopify_fulfilment_product_variant_id = fields.Char(string='Variant Id', readonly=1)
    shopify_fulfilment_product_title = fields.Char(string='Product Title Name', readonly=1)
    shopify_fulfilment_product_name = fields.Char(string='Product Name', readonly=1)
    shopify_fulfilment_product_sku = fields.Char(string='Product Sku', readonly=1)
    shopify_fulfilment_service = fields.Char(string='Product Sku', readonly=1)
    shopify_fulfilment_qty = fields.Integer(string='Fulfilled Qty', readonly=1)
    shopify_fulfilment_grams = fields.Integer(string='Weight(grams) ', readonly=1)
    shopify_fulfilment_price = fields.Float(string='Price', readonly=1)
    shopify_fulfilment_total_discount = fields.Float(string='Discount', readonly=1)
    shopify_fulfilment_status = fields.Char(string='Status', readonly=1)




