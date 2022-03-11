# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, exceptions, api, _
import re
import logging
_logger = logging.getLogger(__name__)


class SaleOrderShopify(models.Model):
    _inherit = 'sale.order'

    shopify_id = fields.Char(string="Shopify Id", readonly=True,
                             store=True)
    shopify_order = fields.Char(string="Shopify Order", readonly=True,
                             store=True)

    marketplace_type = fields.Selection(
        [('shopify', 'Shopify')], string="Marketplace Type"
    )
    shopify_status = fields.Char(string="shopify status", readonly=True)
    shopify_order_date = fields.Datetime(string="shopify Order Date")
    shopify_carrier_service = fields.Char(string="shopify Carrier Service")
    shopify_has_delivery = fields.Boolean(
        string="shopify has delivery", readonly=True, default=False, compute='shopifyhasdelviery')
    shopify_browser_ip = fields.Char(string='Browser IP',)
    shopify_buyer_accepts_marketing = fields.Boolean(
        string='Buyer Merketing',
    )
    shopify_cancel_reason = fields.Char(
        string='Cancel Reason',
    )
    shopify_cancelled_at = fields.Datetime(
        string='Cancel At',
    )
    shopify_cart_token = fields.Char(
        string='Cart Token',
    )
    shopify_checkout_token = fields.Char(
        string='Checkout Token',
    )
    shopify_currency = fields.Many2one(
        string='Shop Currency',
        comodel_name='res.currency',
        ondelete='restrict',
    )
    shopify_financial_status = fields.Selection(
        string='Financial Status',
        selection=[('pending', 'Pending'),
                   ('authorized', 'Authorized'),
                   ('partially_paid', 'Partially Paid'),
                   ('paid', 'Paid'),
                   ('partially_refunded', 'Partially Refunded'),
                   ('voided', 'Voided')
                   ], default='pending'

    )
    shopify_fulfillment_status = fields.Char(
        string='Fullfillment Status',
    )
    shopify_track_updated = fields.Boolean(
        string='Shopify Track Updated',
        default=False,
        readonly=True,
    )
    shopify_transaction_ids = fields.One2many(
        string='Shopify Transaction',
        comodel_name='shopify.transactions',
        inverse_name='sale_id',
    )
    
    


    def fetch_shopify_payments(self):
        _logger.info("fetch_shopify_payments")
        for rec in self:
            if rec.shopify_id:
                marketplace_instance_id = self._get_instance_id()
                version = marketplace_instance_id.marketplace_api_version or '2021-01'
                url = marketplace_instance_id.marketplace_host +  '/admin/api/%s/orders/%s/transactions.json' %(version,self.shopify_id)
                headers = {'X-Shopify-Access-Token':marketplace_instance_id.marketplace_api_password}
                type_req = 'GET'
                try:
                    transactions_list = self.env['marketplace.connector'].marketplace_api_call(headers=headers, url=url, type=type_req,marketplace_instance_id=marketplace_instance_id)
                    if transactions_list.get('transactions'):
                        self.process_shopify_transactions(transactions_list['transactions'])
                    transactions = transactions_list['transactions']
                    for transaction in transactions:
                        _logger.warning("transaction-%s"%(transaction))

                except Exception as e:
                    _logger.warning("Exception-%s"%(e.args))
        

    def process_shopify_transactions(self, transactions):
        for transaction in transactions:
            sp_tran = self.env['shopify.transactions'].sudo()
            tran_id = sp_tran.search([('shopify_id','=',transaction['id'])])
            if not tran_id:
                vals = {'sale_id':self.id, 'shopify_payment_details_id':[],'shopify_payment_receipt_id':[]}
                transaction = {k: v for k, v in transaction.items() if v is not False and v is not None}
                for key, value in transaction.items():
                    print(key,value)
                    if 'shopify_' + str(key) in list(sp_tran._fields) and key not in ['receipt','payment_details']:
                        vals['shopify_' + str(key)] = str(value)




                if transaction.get('receipt'):
                    if type(transaction.get('receipt')) == dict:
                        vals['shopify_payment_details_id'] += [(0,0,transaction.get('receipt'))]
                        self.env['shopify.payment.receipt'].sudo().create(transaction.get('receipt'))
                    if type(transaction.get('receipt')) == list:
                        for receipt in transaction.get('receipt'):
                            vals['shopify_payment_details_id'] += [(0,0,receipt)]

                if transaction.get('payment_details'):
                    if type(transaction.get('payment_details')) == dict:
                        vals['shopify_payment_details_id'] += [(0,0,transaction.get('payment_details'))]
                        self.env['shopify.payment.details'].sudo().create(transaction.get('payment_details'))
                    if type(transaction.get('payment_details')) == list:
                        for pd in transaction.get('payment_details'):
                            vals['shopify_payment_details_id'] += [(0,0,pd)]
                


                tran_id = sp_tran.create(vals)
                print("vals===>>>,", vals)
                print("tran_id===>>>", tran_id)




    def fetch_shopify_refunds(self):
        _logger.info("fetch_shopify_refunds")


    def _get_instance_id(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        try:
            marketplace_instance_id = ICPSudo.get_param(
                'syncoria_base_marketplace.marketplace_instance_id')
            marketplace_instance_id = [int(s) for s in re.findall(
                r'\b\d+\b', marketplace_instance_id)]
        except:
            marketplace_instance_id = False

        if marketplace_instance_id:
            marketplace_instance_id = self.env['marketplace.instance'].sudo().search(
                [('id', '=', marketplace_instance_id[0])])
        return marketplace_instance_id



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    shopify_id = fields.Char(string="Shopify Id", readonly=True,
                             store=True)
    marketplace_type = fields.Selection(
        [('shopify', 'Shopify')], string="Marketplace Type"
    )