# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, exceptions, api, _
import logging
_logger = logging.getLogger(__name__)



class ShopifyRefunds(models.Model):
    _name = 'shopify.refunds'
    _description = 'Shopify Refunds'
    _rec_name = 'name'


    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.transactions'))
    sale_id = fields.Many2one(
        string='Order',
        comodel_name='sale.order',
        ondelete='restrict',
    )
    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    shopify_id = fields.Char(string='Shopify Id', readonly=1)
    shopify_id = fields.Char(string='Id', readonly=1)
    shopify_order_id = fields.Char(string='Order Id', readonly=1)
    shopify_note = fields.Char(string='Note', readonly=1)
    shopify_user_id = fields.Char(string='User Id', readonly=1)
    shopify_processed_at = fields.Char(string='Processed At', readonly=1)
    shopify_restock = fields.Boolean(
        string='Shopify Restock',
    )
    shopify_admin_graphql_api_id = fields.Char(string='Admin Graphql Api Id', readonly=1)
    shopify_transaction_id = fields.Many2one(
        string='Transaction ID',
        comodel_name='shopify.transactions',
        ondelete='restrict',
    )
    #####################################################################
    ################Not RFequired########################################
    #####################################################################
    shopify_kind = fields.Char(string='Kind', readonly=1)
    shopify_gateway = fields.Char(string='Gateway', readonly=1)
    shopify_status = fields.Char(string='Status', readonly=1)
    shopify_message = fields.Char(string='Message', readonly=1)
    shopify_created_at = fields.Char(string='Created At', readonly=1)
    shopify_test = fields.Char(string='Test', readonly=1)
    shopify_authorization = fields.Char(string='Authorization', readonly=1)
    shopify_location_id = fields.Char(string='Location Id', readonly=1)
    shopify_parent_id = fields.Char(string='Parent Id', readonly=1)
    shopify_device_id = fields.Char(string='Device Id', readonly=1)
    shopify_error_code = fields.Char(string='Error Code', readonly=1)
    shopify_source_name = fields.Char(string='Source Name', readonly=1)
    shopify_receipt = fields.Char(string='Receipt', readonly=1)
    shopify_currency_exchange_adjustment = fields.Char(string='Currency Exchange Adjustment', readonly=1)
    shopify_amount = fields.Char(string='Amount', readonly=1)
    shopify_currency = fields.Char(string='Currency', readonly=1)