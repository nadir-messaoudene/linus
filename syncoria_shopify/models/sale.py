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
        selection_add= [('shopify', 'Shopify')],
        string="Marketplace Type"
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
    shopify_refund_ids = fields.One2many(
        string='Shopify Refunds',
        comodel_name='shopify.refunds',
        inverse_name='sale_id',
    )

    def fetch_shopify_payments(self):
        _logger.info("fetch_shopify_payments")
        message = ''
        for rec in self:
            if rec.shopify_id:
                marketplace_instance_id = rec.shopify_instance_id
                version = marketplace_instance_id.marketplace_api_version or '2021-01'
                url = marketplace_instance_id.marketplace_host +  '/admin/api/%s/orders/%s/transactions.json' %(version, rec.shopify_id)
                headers = {'X-Shopify-Access-Token':marketplace_instance_id.marketplace_api_password}
                type_req = 'GET'
                try:
                    transactions_list,next_link = self.env['marketplace.connector'].marketplace_api_call(
                        headers=headers, 
                        url=url, 
                        type=type_req,
                        marketplace_instance_id=marketplace_instance_id
                    )
                    if transactions_list.get('transactions'):
                        message += '\nLength of Transaction List-{}'.format(len(transactions_list.get('transactions')))
                        tran_recs = rec.process_shopify_transactions(transactions_list['transactions'])
                        message += '\nTransaction Record Created-{}'.format(len(tran_recs))
                    rec.message_post(body=_(message))
                except Exception as e:
                    _logger.warning("Exception-%s"%(e.args))
        
    def process_shopify_transactions(self, transactions):
        tran_recs = []
        for transaction in transactions:
            sp_tran = self.env['shopify.transactions'].sudo()
            tran_id = sp_tran.search([('shopify_id','=',transaction['id'])])
            if not tran_id:
                vals = {
                    'sale_id': self.id, 
                    'shopify_instance_id':self.shopify_instance_id.id,
                }
                transaction = {k: v for k, v in transaction.items() if v is not False and v is not None}
                for key, value in transaction.items():
                    if 'shopify_' + str(key) in list(sp_tran._fields) and key not in ['receipt','payment_details']:
                        vals['shopify_' + str(key)] = str(value)

                receipt_vals_list = []
                payment_details_vals_list = []

                if transaction.get('receipt'):
                    if type(transaction.get('receipt')) == dict:
                        receipt = transaction.get('receipt')
                        if receipt:
                            receipt_vals = {}
                            receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                            for key, value in receipt.items():
                                if key in receipt_fields:
                                    receipt_vals[key] = value
                            receipt_vals_list += [receipt_vals]
                            
                    if type(transaction.get('receipt')) == list:
                        for receipt in transaction.get('receipt'):
                            if receipt:
                                receipt_vals = {}
                                receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                                for key, value in receipt.items():
                                    if key in receipt_fields:
                                        receipt_vals[key] = value
                                receipt_vals_list += [receipt_vals]

                if transaction.get('payment_details'):
                    if type(transaction.get('payment_details')) == dict:
                        payment_details = transaction.get('payment_details')
                        if payment_details:
                            payment_details_vals = {}
                            payment_details_fields = list(self.env['shopify.payment.details']._fields)
                            for key, value in payment_details.items():
                                if key in payment_details_fields:
                                    payment_details_vals[key] = value
                            payment_details_vals_list += [payment_details_vals]

                    if type(transaction.get('payment_details')) == list:
                        for payment_details in transaction.get('payment_details'):
                            if payment_details:
                                payment_details_vals = {}
                                payment_details_fields = list(self.env['shopify.payment.details']._fields)
                                for key, value in payment_details.items():
                                    if key in payment_details_fields:
                                        payment_details_vals[key] = value
                                payment_details_vals_list += [payment_details_vals]
                

                tran_id = sp_tran.create(vals)
                if receipt_vals_list:
                    for rv in receipt_vals_list:
                        rv['shopify_instance_id'] = self.shopify_instance_id.id
                    receipt_id = self.env['shopify.payment.receipt'].create(receipt_vals_list)
                    if tran_id and receipt_id:
                        tran_id.shopify_payment_receipt_id = receipt_id[0].id
                        
                if payment_details_vals_list:
                    for pdv in payment_details_vals_list:
                        pdv['shopify_instance_id'] = self.shopify_instance_id.id
                    detail_id = self.env['shopify.payment.details'].create(payment_details_vals_list)
                    if tran_id and detail_id:
                        tran_id.shopify_payment_details_id = detail_id[0].id

                tran_recs.append(tran_id.id)
        return tran_recs

    def fetch_shopify_refunds(self):
        _logger.info("fetch_shopify_refunds")
        message = ''
        for rec in self:
            if rec.shopify_id:
                marketplace_instance_id = rec.shopify_instance_id
                version = marketplace_instance_id.marketplace_api_version or '2021-01'
                url = marketplace_instance_id.marketplace_host +  '/admin/api/%s/orders/%s/refunds.json' %(version, rec.shopify_id)
                headers = {'X-Shopify-Access-Token':marketplace_instance_id.marketplace_api_password}
                type_req = 'GET'
                try:
                    refunds_list = self.env['marketplace.connector'].marketplace_api_call(headers=headers, url=url, type=type_req,marketplace_instance_id=marketplace_instance_id)
                    if refunds_list.get('refunds'):
                        message = '\nLength of Refund List-{}'.format(len(refunds_list.get('refunds')))
                        refund_recs = self.process_shopify_refund(refunds_list['refunds'])
                        message += '\Refund Record Created-{}'.format(len(refund_recs))
                    rec.message_post(body=_(message))
                except Exception as e:
                    _logger.warning("Exception-%s"%(e.args))

    def process_shopify_refund(self, refunds):
        refunds_recs = []
        for refund in refunds:
            sp_refunds = self.env['shopify.refunds'].sudo()
            refund_id = sp_refunds.search([('shopify_id','=',refund['id'])])
            if not refund_id:
                vals = {'sale_id': self.id}
                refund = {k: v for k, v in refund.items() if v is not False and v is not None}
                for key, value in refund.items():
                    if 'shopify_' + str(key) in list(sp_refunds._fields) and key not in ['receipt','payment_details']:
                        vals['shopify_' + str(key)] = str(value)
                refund_id = sp_refunds.create(vals)
                refunds_recs.append(refund_id.id)
        return refunds_recs


    def process_shopify_invoice(self):
        message = ""
        account_move = self.env['account.move'].sudo()
        move_id = False
        for rec in self:
            success_tran_ids = rec.shopify_transaction_ids.filtered(lambda l:l.shopify_status == 'success')
            paid_amount = sum([ float(amount) for amount in success_tran_ids.mapped('shopify_amount')])
            if rec.amount_total == paid_amount:
                move_id = account_move.search([('name', '=', rec.name)])
                if not move_id:
                    message += "\nCreating Invoice for Sale Order-{}".format(rec)
                    wiz = self.env['sale.advance.payment.inv'].sudo().with_context(
                        active_ids=rec.ids, 
                        open_invoices=True).create({})
                    wiz.sudo().create_invoices()
                    move_id = account_move.search([('name', '=', rec.name)])

                if move_id and move_id.state != 'posted':
                    move_id.action_confirm()
                    message += "\nInvoice-{} Posted for Sale Order-{}".format(move_id, rec)
                try:
                    move_id._cr.commit()
                except Exception as e:
                    _logger.warning("Exception-{}".format(e.args))
        return move_id, message

    def shopify_invoice_register_payments(self):
        message = ""
        account_move = self.env['account.move'].sudo()
        account_payment = self.env['account.move'].sudo()
        move_id = False
        for rec in self:
            success_tran_ids = rec.shopify_transaction_ids.filtered(lambda l:l.shopify_status == 'success')
            move_id = account_move.search([('name', '=', rec.name)])
            for tran_id in success_tran_ids:
                shopify_instance_id = tran_id.shopify_instance_id or rec.shopify_instance_id
                if float(tran_id.shopify_amount) > 0 and shopify_instance_id:
                    wizard_vals = {
                        'journal_id':shopify_instance_id.marketplace_payment_journal_id.id,
                        'payment_method_line_id':shopify_instance_id.marketplace_payment_journal_id.id,
                        'amount': float(tran_id.shopify_amount),
                        'payment_date': fields.Datetime.now(),
                    }
                    wizard_vals['payment_date'] = tran_id.shopify_processed_at.split('T')[0] if tran_id.shopify_processed_at else fields.Datetime.now()
                    domain = []
                    for move in move_id:
                        domain += [('ref', '=', move.name)]
                    if domain:
                        pay_id = account_payment.search(domain)
                        if pay_id:
                            wizard_vals['communication'] = pay_id.ref.split('-')[0]

                    pmt_wizard = self.env['account.payment.register'].with_context(
                        active_model='account.move', 
                        active_ids=rec.ids).create(wizard_vals)

                    pmt_wizard.action_create_payments()
                    
                    # try:
                    #     move_id._cr.commit()
                    # except Exception as e:
                    #     _logger.warning("Exception-{}".format(e.args))
        return move_id, message


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    shopify_id = fields.Char(string="Shopify Id", readonly=True, store=True)
    marketplace_type = fields.Selection(
        [('shopify', 'Shopify')], string="Marketplace Type"
    )