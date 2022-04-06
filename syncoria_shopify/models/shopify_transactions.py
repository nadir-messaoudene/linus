# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, exceptions, api, _
import logging
_logger = logging.getLogger(__name__)



class ShopifyTransactions(models.Model):
    _name = 'shopify.transactions'
    _description = 'Shopify Transactions'
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
    shopify_order_id = fields.Char(string='Order Id', readonly=1)
    shopify_kind = fields.Char(string='Kind', readonly=1)
    shopify_gateway = fields.Char(string='Gateway', readonly=1)
    shopify_status = fields.Char(string='Status', readonly=1)
    shopify_message = fields.Char(string='Message', readonly=1)
    shopify_created_at = fields.Char(string='Created At', readonly=1)
    shopify_test = fields.Char(string='Test', readonly=1)
    shopify_authorization = fields.Char(string='Authorization', readonly=1)
    shopify_location_id = fields.Char(string='Location Id', readonly=1)
    shopify_user_id = fields.Char(string='User Id', readonly=1)
    shopify_parent_id = fields.Char(string='Parent Id', readonly=1)
    shopify_processed_at = fields.Char(string='Processed At', readonly=1)
    shopify_device_id = fields.Char(string='Device Id', readonly=1)
    shopify_error_code = fields.Char(string='Error Code', readonly=1)
    shopify_source_name = fields.Char(string='Source Name', readonly=1)
    shopify_receipt = fields.Char(string='Receipt', readonly=1)
    shopify_currency_exchange_adjustment = fields.Char(string='Currency Exchange Adjustment', readonly=1)
    shopify_amount = fields.Char(string='Amount', readonly=1)
    shopify_currency = fields.Char(string='Currency', readonly=1)
    shopify_admin_graphql_api_id = fields.Char(string='Admin Graphql Api Id', readonly=1)
    shopify_payment_details = fields.Char(string='Payment Details', readonly=1)
    shopify_payment_details_id = fields.Many2one(
        string='Payment Details IDs',
        comodel_name='shopify.payment.details',
        ondelete='restrict',
    )
    shopify_payment_receipt_id = fields.Many2one(
        string='Receipt IDs',
        comodel_name='shopify.payment.receipt',
        ondelete='restrict',
    )
    shopify_is_process = fields.Boolean(string="Is processed" ,default=False)
    shopify_exchange_rate = fields.Char(string='Exchange Rate', readonly=1)
    


class ShopifyPaymentDetails(models.Model):
    _name = 'shopify.payment.details'
    _description = 'Shopify Payment Details'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.payment.details'))
    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    credit_card_bin = fields.Char(string='CC Bin', readonly=1)
    avs_result_code = fields.Char(string='AVS Result Code', readonly=1)
    cvv_result_code = fields.Char(string='CVV Result Code', readonly=1)
    credit_card_number = fields.Char(string='CC Number', readonly=1)
    credit_card_company = fields.Char(string='CC Company', readonly=1)
    credit_card_name = fields.Char(string='CC Name', readonly=1)
    credit_card_wallet = fields.Char(string='CC Wallet', readonly=1)
    credit_card_expiration_month = fields.Char(string='CC Expiration Month', readonly=1)
    credit_card_expiration_year = fields.Char(string='CC Expiration Year', readonly=1)
    


class ShopifyPaymentReceipt(models.Model):
    _name = 'shopify.payment.receipt'
    _description = 'Shopify Payment Receipt'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.payment.receipt'))

    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    testcase = fields.Char(string='CC Bin', readonly=1)
    authorization = fields.Char(string='AVS Result Code', readonly=1)
    paid_amount = fields.Char(readonly=1)
    