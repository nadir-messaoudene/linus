# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from locale import currency
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
        selection_add=[('shopify', 'Shopify')],
        string="Marketplace Type"
    )
    shopify_status = fields.Char(string="shopify status", readonly=True)
    shopify_order_date = fields.Datetime(string="shopify Order Date")
    shopify_carrier_service = fields.Char(string="shopify Carrier Service")
    shopify_has_delivery = fields.Boolean(
        string="shopify has delivery", readonly=True, default=False, compute='shopifyhasdelviery')
    shopify_browser_ip = fields.Char(string='Browser IP', )
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
                   ('voided', 'Voided'),
                   ('refunded', 'Refunded')
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
    shopify_refund_transaction_ids = fields.One2many(
        string='Shopify Refunds Transaction',
        comodel_name='shopify.refunds.transaction',
        inverse_name='sale_id',
    )
    shopify_fulfilment_ids = fields.One2many(
        string='Shopify Fulfilment',
        comodel_name='shopify.fulfilment',
        inverse_name='sale_order_id',
    )
    shopify_is_invoice = fields.Boolean(string="Is shopify invoice paid?",default=False)
    shopify_is_refund = fields.Boolean(string="Is shopify credit note paid?",default=False)
    transaction_fee_tax_amount = fields.Monetary()
    transaction_fee_total_amount = fields.Monetary()
    refund_fee_tax_amount = fields.Monetary()
    refund_fee_total_amount = fields.Monetary()
    shopify_tag_ids = fields.Many2many('crm.tag', string="Shopify Tags")

    def fetch_shopify_payments(self):
        _logger.info("fetch_shopify_payments")
        message = ''
        for rec in self:
            if rec.shopify_id:
                marketplace_instance_id = rec.shopify_instance_id
                version = marketplace_instance_id.marketplace_api_version or '2021-01'
                url = marketplace_instance_id.marketplace_host + '/admin/api/%s/orders/%s/transactions.json' % (
                version, rec.shopify_id)
                headers = {'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password}
                type_req = 'GET'
                try:
                    transactions_list, next_link = self.env['marketplace.connector'].marketplace_api_call(
                        headers=headers,
                        url=url,
                        type=type_req,
                        marketplace_instance_id=marketplace_instance_id
                    )
                    if transactions_list.get('transactions'):
                        message += '\nLength of Transaction List-{}'.format(len(transactions_list.get('transactions')))
                        tran_recs = rec.process_shopify_transactions(transactions_list['transactions'])
                        message += '\nTransaction Record Created-{}'.format(len(tran_recs))
                    if tran_recs:
                        rec.message_post(body=_(message))
                except Exception as e:
                    _logger.warning("Exception-%s" % (e.args))

    def process_shopify_transactions(self, transactions):
        tran_recs = []
        for transaction in transactions:
            sp_tran = self.env['shopify.transactions'].sudo()
            tran_id = sp_tran.search([('shopify_id', '=', transaction['id'])])
            if not tran_id and transaction.get('kind') != 'refund':
                vals = {
                    'sale_id': self.id,
                    'shopify_instance_id': self.shopify_instance_id.id,
                }
                transaction = {k: v for k, v in transaction.items() if v is not False and v is not None}
                for key, value in transaction.items():
                    if 'shopify_' + str(key) in list(sp_tran._fields) and key not in ['receipt', 'payment_details']:
                        vals['shopify_' + str(key)] = str(value)

                receipt_vals_list = []
                payment_details_vals_list = []


                try:
                    exchange_rate = "1.0000"
                    if transaction.get('currency'):
                        if transaction.get('currency') == self.pricelist_id.currency_id.name:
                            exchange_rate = "1.0000"
                            vals['shopify_exchange_rate'] = exchange_rate
                        else:
                            _logger.info("Transaction Currency do not match with Sale Order Pricelist Currency")
                except Exception as e:
                    _logger.warning("Exception-{}".format(e.args))


                if transaction.get('receipt'):
                    if type(transaction.get('receipt')) == dict:
                        receipt = transaction.get('receipt')
                        if receipt:
                            receipt_vals = {}
                            receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                            for key, value in receipt.items():
                                if key in receipt_fields:
                                    receipt_vals[key] = value
                            metadata_vals_list = self.process_receipt_metadata(receipt=receipt, tran_type='sale')
                            if metadata_vals_list:
                                receipt_vals['shopify_receipt_metadata_ids'] = metadata_vals_list

                            receipt_vals_list += [receipt_vals]
                            ########################################################################################################
                            try:
                                #Populate Exchange Rate:
                                if receipt.get('charges',{}).get('data',{}) and transaction.get('amount') and receipt.get('amount'):
                                    if float(transaction.get('amount')) == float(receipt.get('amount')/100):
                                        data = receipt.get('charges',{}).get('data',{})
                                        for data_item in data:
                                            if float(transaction.get('amount')) == float(data_item.get('amount')/100):
                                                if data_item.get('balance_transaction',{}).get('exchange_rate'):
                                                    vals['shopify_exchange_rate'] = data_item.get('balance_transaction',{}).get('exchange_rate')
                                                    print("exchange_rate===>>>{}".format(exchange_rate))
                                
                            except Exception as e:
                                _logger.warning("Exception-{}".format(e.args))
                            #######################################################################################################

                    if type(transaction.get('receipt')) == list:
                        for receipt in transaction.get('receipt'):
                            if receipt:
                                receipt_vals = {}
                                receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                                for key, value in receipt.items():
                                    if key in receipt_fields:
                                        receipt_vals[key] = value
                                metadata_vals_list = self.process_receipt_metadata(receipt=receipt, tran_type='sale')
                                if metadata_vals_list:
                                    receipt_vals['shopify_receipt_metadata_ids'] = metadata_vals_list
                                receipt_vals_list += [receipt_vals]

                                ########################################################################################################
                                try:
                                    #Populate Exchange Rate:
                                    if receipt.get('charges',{}).get('data',{}) and transaction.get('amount') and receipt.get('amount'):
                                        if float(transaction.get('amount')) == float(receipt.get('amount')/100):
                                            data = receipt.get('charges',{}).get('data',{})
                                            for data_item in data:
                                                if float(transaction.get('amount')) == float(data_item.get('amount')/100):
                                                    if data_item.get('balance_transaction',{}).get('exchange_rate'):
                                                        vals['shopify_exchange_rate'] = data_item.get('balance_transaction',{}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))
                                    
                                except Exception as e:
                                    _logger.warning("Exception-{}".format(e.args))
                                #######################################################################################################


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

    def process_receipt_metadata(self, receipt, tran_type):
        vals_list = []
        print("tran_type===>>>", tran_type)
        if receipt.get('charges',{}).get('data',{}):
            data = receipt.get('charges',{}).get('data',{})
            for data_item in data:
                vals = data_item.get('metadata')
                if vals:
                    vals.update({
                        'name' : self.env['ir.sequence'].next_by_code('shopify.payment.receipt.metadata'),
                        'shopify_instance_id' : self.shopify_instance_id.id, 
                        'company_id' : self.company_id.id, 
                        'sale_id' : self.id, 
                        'transaction_type' : tran_type
                    })
                    if data_item.get('currency'):
                        currency = data_item.get('currency').upper()
                        print("currency===>>>", currency)
                        currency_id = self.env['res.currency'].sudo().search([('name', '=', currency)], limit=1)
                        print("currency_id===>>>", currency_id)
                        if currency_id:
                            vals['currency_id'] = currency_id.id

                    print("vals===>>>", vals)


                    vals_list += [(0,0, vals)]

        return vals_list


    def fetch_shopify_refunds(self):
        _logger.info("fetch_shopify_refunds")
        message = ''
        for rec in self:
            if rec.shopify_id:
                marketplace_instance_id = rec.shopify_instance_id
                version = marketplace_instance_id.marketplace_api_version or '2021-01'
                url = marketplace_instance_id.marketplace_host + '/admin/api/%s/orders/%s/refunds.json' % (
                version, rec.shopify_id)
                headers = {'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password}
                type_req = 'GET'
                try:
                    refunds_list, next_link = self.env['marketplace.connector'].marketplace_api_call(headers=headers,
                                                                                                     url=url,
                                                                                                     type=type_req,
                                                                                                     marketplace_instance_id=marketplace_instance_id)
                    if refunds_list.get('refunds'):
                        message = '\nLength of Refund List-{}'.format(len(refunds_list.get('refunds')))
                        refund_recs = self.process_shopify_refund(refunds_list['refunds'])
                        refund_recs_transaction = self.process_shopify_refund_transaction(refunds_list['refunds'])
                        message += '\Refund Record Created-{}\n'.format(len(refund_recs))
                        message += '\Refund Transaction Record Created-{}'.format(len(refund_recs_transaction))
                    rec.message_post(body=_(message))
                except Exception as e:
                    _logger.warning("Exception-%s" % (e.args))

    def process_shopify_refund(self, refunds):
        refunds_recs = []
        for refund in refunds:
            sp_refunds = self.env['shopify.refunds'].sudo()
            refund_id = sp_refunds.search([('shopify_id', '=', refund['id'])])
            if not refund_id:
                vals = {
                    'sale_id': self.id,
                    'shopify_instance_id': self.shopify_instance_id.id,
                }
                refund = {k: v for k, v in refund.items() if v is not False and v is not None}
                for key, value in refund.items():
                    if 'shopify_' + str(key) in list(sp_refunds._fields) and key not in ['receipt', 'payment_details']:
                        vals['shopify_' + str(key)] = str(value)
                refund_id = sp_refunds.create(vals)
                refunds_recs.append(refund_id.id)
        return refunds_recs

    def process_shopify_refund_transaction(self, transactions):
        tran_recs = []
        for tran in transactions:
            for transaction in tran.get('transactions'):
                sp_tran = self.env['shopify.refunds.transaction'].sudo()
                tran_id = sp_tran.search([('shopify_refund_id', '=', transaction['id'])])
                if not tran_id:
                    vals = {
                        'sale_id': self.id,
                        'shopify_instance_id': self.shopify_instance_id.id,
                    }
                    transaction = {k: v for k, v in transaction.items() if v is not False and v is not None}
                    for key, value in transaction.items():
                        if 'shopify_refund_' + str(key) in list(sp_tran._fields) and key not in ['receipt',
                                                                                                 'payment_details']:
                            vals['shopify_refund_' + str(key)] = str(value)

                    receipt_vals_list = []
                    payment_details_vals_list = []

                    try:
                        exchange_rate = "1.0000"
                        if transaction.get('currency'):
                            if transaction.get('currency') == self.pricelist_id.currency_id.name:
                                exchange_rate = "1.0000"
                                vals['shopify_refund_exchange_rate'] = exchange_rate
                            else:
                                _logger.info("Transaction Currency do not match with Sale Order Pricelist Currency")
                    except Exception as e:
                        _logger.warning("Exception-{}".format(e.args))



                    if transaction.get('receipt'):
                        if type(transaction.get('receipt')) == dict:
                            receipt = transaction.get('receipt')
                            if receipt:
                                receipt_vals = {}
                                receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                                for key, value in receipt.items():
                                    if key in receipt_fields:
                                        receipt_vals[key] = value

                                metadata_vals_list = self.process_receipt_metadata(receipt=receipt, tran_type='refund')
                                if metadata_vals_list:
                                    receipt_vals['shopify_receipt_metadata_ids'] = metadata_vals_list
                                receipt_vals_list += [receipt_vals]
                                ########################################################################################################
                                try:
                                    #Populate Exchange Rate:
                                    if receipt.get('charges',{}).get('data',{}) and transaction.get('amount') and receipt.get('amount'):
                                        if float(transaction.get('amount')) == float(receipt.get('amount')/100):
                                            data = receipt.get('charges',{}).get('data',{})
                                            for data_item in data:
                                                if float(transaction.get('amount')) == float(data_item.get('amount')/100):
                                                    if data_item.get('balance_transaction',{}).get('exchange_rate'):
                                                        vals['shopify_refund_exchange_rate'] = data_item.get('balance_transaction',{}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))
                                    
                                except Exception as e:
                                    _logger.warning("Exception-{}".format(e.args))
                                #######################################################################################################



                        if type(transaction.get('receipt')) == list:
                            for receipt in transaction.get('receipt'):
                                if receipt:
                                    receipt_vals = {}
                                    receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                                    for key, value in receipt.items():
                                        if key in receipt_fields:
                                            receipt_vals[key] = value

                                    metadata_vals_list = self.process_receipt_metadata(receipt=receipt, tran_type='refund')
                                    if metadata_vals_list:
                                        receipt_vals['shopify_receipt_metadata_ids'] = metadata_vals_list
                                    receipt_vals_list += [receipt_vals]
                                    
                                    ########################################################################################################
                                    try:
                                        #Populate Exchange Rate:
                                        if receipt.get('charges',{}).get('data',{}) and transaction.get('amount') and receipt.get('amount'):
                                            if float(transaction.get('amount')) == float(receipt.get('amount')/100):
                                                data = receipt.get('charges',{}).get('data',{})
                                                for data_item in data:
                                                    if float(transaction.get('amount')) == float(data_item.get('amount')/100):
                                                        if data_item.get('balance_transaction',{}).get('exchange_rate'):
                                                            vals['shopify_refund_exchange_rate'] = data_item.get('balance_transaction',{}).get('exchange_rate')
                                                            print("exchange_rate===>>>{}".format(exchange_rate))
                                        
                                    except Exception as e:
                                        _logger.warning("Exception-{}".format(e.args))
                                    #######################################################################################################



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
                            tran_id.shopify_refund_payment_receipt_id = receipt_id[0].id

                    if payment_details_vals_list:
                        for pdv in payment_details_vals_list:
                            pdv['shopify_instance_id'] = self.shopify_instance_id.id
                        detail_id = self.env['shopify.payment.details'].create(payment_details_vals_list)
                        if tran_id and detail_id:
                            tran_id.shopify_refund_payment_details_id = detail_id[0].id

                    tran_recs.append(tran_id.id)
        return tran_recs

    def process_shopify_invoice(self):
        message = ""
        account_move = self.env['account.move'].sudo()
        move_id = False
        for rec in self:
            success_tran_ids = rec.shopify_transaction_ids.filtered(lambda l: l.shopify_status == 'success')
            # paid_amount = sum([ float(amount) for amount in success_tran_ids.mapped('shopify_amount')])
            if success_tran_ids and not rec.shopify_is_invoice and rec.state not in ("cancel"):
                move_id = account_move.search([('invoice_origin', '=', rec.name), ('move_type', "=", "out_invoice")])
                if not move_id:
                    message += "\nCreating Invoice for Sale Order-{}".format(rec)
                    wiz = self.env['sale.advance.payment.inv'].sudo().with_context(
                        active_ids=rec.ids,
                        open_invoices=True).create({})
                    wiz.sudo().create_invoices()
                    move_id = account_move.search(
                        [('invoice_origin', '=', rec.name), ('move_type', "=", "out_invoice")])

                if move_id and move_id.state != 'posted':
                    ################################################################################################
                    #Update Analytic Accounts for Shopify
                    try:
                        if not move_id.shopify_instance_id:
                            move_id.write({'shopify_instance_id' : rec.shopify_instance_id.id})
                        # if move_id.shopify_instance_id:
                        #     for line in move_id.invoice_line_ids:
                        #         line.analytic_account_id =  move_id.shopify_instance_id.analytic_account_id.id
                    except Exception as e:
                        _logger.warning("Update Analytic Accounts Exception-{}".format(e.args))
                    ################################################################################################

                    move_id.action_post()
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
            success_tran_ids = rec.shopify_transaction_ids.filtered(lambda l: l.shopify_status == 'success')
            move_id = account_move.search([('invoice_origin', '=', rec.name), ('move_type', "=", "out_invoice")])
            try:
                if move_id:
                    for tran_id in success_tran_ids:
                        shopify_instance_id = tran_id.shopify_instance_id or rec.shopify_instance_id
                        if float(tran_id.shopify_amount) > 0 and shopify_instance_id and move_id.payment_state != 'in_payment':
                            #######################################################################################################
                            shopify_amount = float(tran_id.shopify_amount)
                            if tran_id.shopify_currency and tran_id.shopify_amount:
                                if tran_id.shopify_currency != tran_id.shopify_instance_id.pricelist_id.currency_id.name:
                                    shopify_amount = float(tran_id.shopify_amount)*float(tran_id.shopify_exchange_rate)
                            #######################################################################################################
                            _logger.info("shopify_amount==>>>{}".format(shopify_amount))
                            wizard_vals = {
                                'journal_id': shopify_instance_id.marketplace_payment_journal_id.id,
                                'amount': shopify_amount,
                                'payment_date': fields.Datetime.now(),
                            }

                            payment_method_line_id = shopify_instance_id.marketplace_payment_journal_id.inbound_payment_method_line_ids.filtered(
                                lambda l:l.payment_method_id.id == shopify_instance_id.marketplace_inbound_method_id.id)
                            if payment_method_line_id:
                                wizard_vals['payment_method_line_id'] = payment_method_line_id.id

                            wizard_vals['payment_date'] = tran_id.shopify_processed_at.split('T')[
                                0] if tran_id.shopify_processed_at else fields.Datetime.now()
                            domain = []
                            for move in move_id:
                                domain += [('ref', '=', move.name)]
                            if domain:
                                pay_id = account_payment.search(domain, order='id desc', limit=1)
                                if pay_id:
                                    wizard_vals['communication'] = pay_id.ref.split('-')[0]

                            pmt_wizard = self.env['account.payment.register'].with_context(
                                active_model='account.move',
                                active_ids=move_id.ids).create(wizard_vals)

                            payment = pmt_wizard.action_create_payments()
                            print("===============>", payment)
                            if move_id.payment_state in ['paid','in_payment']:
                                rec.write({"shopify_is_invoice": True})

            except Exception as e:
                _logger.warning("Exception-{}-{}".format(rec.id,e.args))

                # try:
                #     move_id._cr.commit()
                # except Exception as e:
                #     _logger.warning("Exception-{}".format(e.args))
        return move_id, message

    def process_shopify_credit_note(self):
        message = ""
        account_move = self.env['account.move'].sudo()
        move_id = False
        refund_move_id = False
        for rec in self:
            success_tran_ids = rec.shopify_refund_transaction_ids.filtered(
                lambda l: l.shopify_refund_status == 'success')

            if success_tran_ids and  not rec.shopify_is_refund and rec.state not in ("cancel"):
                paid_amount = sum([float(amount) for amount in success_tran_ids.mapped('shopify_refund_amount')])
                shopify_instance_id = rec.shopify_instance_id
                move_id = account_move.search([('invoice_origin', '=', rec.name), ('move_type', "=", "out_invoice")])
                refund_move_id = account_move.search(
                    [('invoice_origin', '=', rec.name), ('move_type', "=", "out_refund")])
                if move_id.payment_state in ['paid', 'in_payment'] and not refund_move_id:
                    message += "\nCreating Creating for Sale Order-{}".format(rec)

                    wizard_vals = {
                        'refund_method': 'refund',
                        'date_mode': 'entry',
                        'journal_id': shopify_instance_id.marketplace_journal_id.id

                    }
                    revasal_wizard = self.env['account.move.reversal'].with_context(
                        active_model='account.move',
                        active_ids=move_id.ids).create(wizard_vals)
                    revasal_wizard.sudo().reverse_moves()
                    refund_move_id = account_move.search([('invoice_origin', '=', rec.name), ('move_type', "=", "out_refund")])

                if refund_move_id and refund_move_id.state == 'draft':
                    refund_move_id.action_post()
                    message += "\nCredit Note-{} Posted for Sale Order-{}".format(refund_move_id, rec)
                try:
                    refund_move_id._cr.commit()
                except Exception as e:
                    _logger.warning("Exception-{}".format(e.args))
        return refund_move_id, message

    def shopify_credit_note_register_payments(self):
        message = ""
        account_move = self.env['account.move'].sudo()
        account_payment = self.env['account.move'].sudo()
        move_id = False
        for rec in self:
            success_tran_ids = rec.shopify_refund_transaction_ids.filtered(
                lambda l: l.shopify_refund_status == 'success')
            move_id = account_move.search([('invoice_origin', '=', rec.name), ('move_type', "=", "out_refund")])
            try:
                if move_id:
                    for tran_id in success_tran_ids:
                        shopify_instance_id = tran_id.shopify_instance_id or rec.shopify_instance_id
                        if float(
                                tran_id.shopify_refund_amount) > 0 and shopify_instance_id and move_id.payment_state != 'in_payment':

                            #######################################################################################################
                            shopify_refund_amount = float(tran_id.shopify_refund_amount)
                            if tran_id.shopify_refund_currency and tran_id.shopify_refund_amount:
                                if tran_id.shopify_refund_currency != tran_id.shopify_instance_id.pricelist_id.currency_id.name:
                                    shopify_refund_amount = float(tran_id.shopify_refund_amount)*float(tran_id.shopify_refund_exchange_rate)
                            #######################################################################################################


                            wizard_vals = {
                                'journal_id': shopify_instance_id.marketplace_refund_journal_id.id,
                                'amount': shopify_refund_amount,
                                'payment_date': fields.Datetime.now(),
                            }

                            payment_method_line_id = shopify_instance_id.marketplace_refund_journal_id.outbound_payment_method_line_ids.filtered(
                                lambda l:l.payment_method_id.id == shopify_instance_id.marketplace_outbound_method_id.id)
                            if payment_method_line_id:
                                wizard_vals['payment_method_line_id'] = payment_method_line_id.id

                            wizard_vals['payment_date'] = tran_id.shopify_refund_processed_at.split('T')[
                                0] if tran_id.shopify_refund_processed_at else fields.Datetime.now()
                            domain = []
                            for move in move_id:
                                domain += [('ref', '=', move.name)]
                            # if domain:
                            #     pay_id = account_payment.search(domain)
                            #     if pay_id:
                            #         wizard_vals['communication'] = pay_id.ref.split('-')[0]

                            pmt_wizard = self.env['account.payment.register'].with_context(
                                active_model='account.move',
                                active_ids=move_id.ids).create(wizard_vals)

                            payment = pmt_wizard.action_create_payments()
                            print("===============>", payment)
                            if move_id.payment_state in ['paid', 'in_payment']:
                                rec.write({"shopify_is_refund": True})
            except Exception as e:
                _logger.warning("Exception-{}-{}".format(rec.id,e.args))
        return move_id, message

    def get_order_fullfillments(self):
        for rec in self:
            marketplace_instance_id = rec.shopify_instance_id
            version = marketplace_instance_id.marketplace_api_version or '2022-01'
            url = marketplace_instance_id.marketplace_host + \
                '/admin/api/%s/orders/%s/fulfillments.json' % (
                    version, rec.shopify_id)
            headers = {
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                'Content-Type': 'application/json'
            }
            type_req = 'GET'
            fullfillment,next_link = self.env[
                'marketplace.connector'].shopify_api_call(
                headers=headers,
                url=url,
                type=type_req,
                marketplace_instance_id=marketplace_instance_id,
                data={}
            )
            _logger.info("\nfullfillment---->" + str(fullfillment))


            if fullfillment.get('errors'):
                raise exceptions.UserError(_(fullfillment.get('errors')))
            else:
                _logger.info("\nSuccess---->")
                if rec.state not in ['cancel'] and fullfillment.get('fulfillments') and marketplace_instance_id.auto_create_fulfilment :
                    shopify_fulfil_obj = self.env['shopify.fulfilment']
                    for fulfillment in fullfillment.get('fulfillments'):
                        exist_fulfilment = shopify_fulfil_obj.search([("shopify_fulfilment_id", "=", fulfillment['id']),
                                                                      ("shopify_instance_id", "=", marketplace_instance_id.id),
                                                                      ("sale_order_id","=",rec.id)],limit=1)

                        fulfillment_vals = {
                            "name": rec.name+'#'+str(fulfillment.get("order_id"))[:3],
                            "sale_order_id": rec.id,
                            "shopify_instance_id": marketplace_instance_id.id,
                            "shopify_order_id": fulfillment.get("order_id"),
                            "shopify_fulfilment_id": fulfillment.get("id"),
                            "shopify_fulfilment_tracking_number": ','.join(fulfillment.get("tracking_numbers")),
                            "shopify_fulfilment_service": ','.join(fulfillment.get("service")),
                          "shopify_fulfilment_status": fulfillment.get("line_items")[0].get("fulfillment_status"),
                            "shopify_status": fulfillment.get("status")
                        }
                        fulfillment_line_vals=[]
                        for line_item in fulfillment.get("line_items"):
                            fulfillment_line_vals +=[(0,0,{
                                "sale_order_id": rec.id,
                                "name":rec.name+":"+line_item.get("name"),
                                "shopify_instance_id": marketplace_instance_id.id,
                              "shopify_fulfilment_line_id": line_item.get("id"),
                             "shopify_fulfilment_product_id": line_item.get("product_id"),
                             "shopify_fulfilment_product_variant_id": line_item.get("variant_id"),
                             "shopify_fulfilment_product_title": line_item.get("title"),
                             "shopify_fulfilment_product_name": line_item.get("name"),
                             "shopify_fulfilment_service": line_item.get("fulfillment_service"),
                             "shopify_fulfilment_qty": line_item.get("quantity"),
                             "shopify_fulfilment_grams": line_item.get("grams"),
                             "shopify_fulfilment_price": line_item.get("price"),
                             "shopify_fulfilment_total_discount": line_item.get("total_discount"),
                             "shopify_fulfilment_status": line_item.get("total_discount"),
                            })]
                        fulfillment_vals["shopify_fulfilment_line"] = fulfillment_line_vals
                        if exist_fulfilment:
                            shopify_fulfil_obj.update(fulfillment_vals)
                        else:
                            shopify_fulfil_obj.create(fulfillment_vals)

    def _process_picking(self,fulfilment,picking,order):
        backorder = False
        move_lines = []
        picking.move_line_ids_without_package.unlink()
        for fulfilment_item in fulfilment.shopify_fulfilment_line:
            product_id = order.order_line.filtered_domain([("product_id.shopify_id", "=",
                                                          fulfilment_item.shopify_fulfilment_product_variant_id)]).product_id
            # move_lines += [(0, 0, {
            #     'name': '/',
            #     'product_id': product_id.id,
            #     'product_uom': product_id.uom_id.id,
            #     'product_uom_qty': fulfilment_item.shopify_fulfilment_qty,
            #     'location_id': rec.picking_ids.location_id.id,
            #     # 'location_dest_id': rec.picking_ids.location_dest_id.id,
            # })]
            # rec.picking_ids.move_line_ids_without_package.unlink()
            if product_id:
                picking.move_line_ids_without_package = [(0, 0, {
                    'company_id': self.env.company.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'product_id': product_id.id,
                    'product_uom_id': product_id.uom_id.id,
                    'qty_done': fulfilment_item.shopify_fulfilment_qty,
                    'product_uom_qty': 0.0,
                })]
            else:
                picking.message_post(body="No associate product %s this shopify product ID"%(fulfilment_item.shopify_fulfilment_product_variant_id))
        # rec.picking_ids.move_lines.state = 'draft'
        # rec.picking_ids.sudo().move_ids_without_package = [(5,[0])]
        # move_lines = [(5, 0), move_lines]

        # pick_output.action_assign()
        picking.shopify_id = fulfilment.shopify_fulfilment_id
        picking.carrier_tracking_ref = fulfilment.shopify_fulfilment_tracking_number
        picking.shopify_service = fulfilment.shopify_fulfilment_service
        picking.action_confirm()
        picking.action_assign()
        validate_picking = picking.button_validate()
        if type(validate_picking) == dict and validate_picking.get('res_model') == 'stock.backorder.confirmation':
            yy = self.env['stock.backorder.confirmation'].with_context(validate_picking.get('context')).process()

        # if picking._check_backorder():
        #     backorder = True
        #
        # return backorder



    def process_shopify_fulfilment(self):
        message = ""
        for rec in self:
            success_fulfilment = rec.shopify_fulfilment_ids.filtered(lambda l: l.shopify_status == 'success')
            # paid_amount = sum([ float(amount) for amount in success_tran_ids.mapped('shopify_amount')])
            if success_fulfilment:
               for fulfilment in success_fulfilment:
                   picking_exist = rec.picking_ids.filtered_domain([('shopify_id',"=",fulfilment.shopify_fulfilment_id)])
                   try:
                       if not picking_exist:
                           if rec.delivery_count ==1 and not rec.picking_ids.shopify_id:
                               self._process_picking(fulfilment,rec.picking_ids,rec)

                               # move_lines = []
                               # rec.picking_ids.move_line_ids_without_package.unlink()
                               # for fulfilment_item in fulfilment.shopify_fulfilment_line:
                               #     product_id = rec.order_line.filtered_domain([("product_id.shopify_id", "=",
                               #                                                   fulfilment_item.shopify_fulfilment_product_variant_id)]).product_id
                               #     # move_lines += [(0, 0, {
                               #     #     'name': '/',
                               #     #     'product_id': product_id.id,
                               #     #     'product_uom': product_id.uom_id.id,
                               #     #     'product_uom_qty': fulfilment_item.shopify_fulfilment_qty,
                               #     #     'location_id': rec.picking_ids.location_id.id,
                               #     #     # 'location_dest_id': rec.picking_ids.location_dest_id.id,
                               #     # })]
                               #     # rec.picking_ids.move_line_ids_without_package.unlink()
                               #
                               #     rec.picking_ids.move_line_ids_without_package = [(0, 0, {
                               #         'company_id': self.env.company.id,
                               #         'location_id': rec.picking_ids.location_id.id,
                               #         'location_dest_id': rec.picking_ids.location_dest_id.id,
                               #         'product_id': product_id.id,
                               #         'product_uom_id': product_id.uom_id.id,
                               #         'qty_done': fulfilment_item.shopify_fulfilment_qty,
                               #         'product_uom_qty': 0.0,
                               #     })]
                               # # rec.picking_ids.move_lines.state = 'draft'
                               # # rec.picking_ids.sudo().move_ids_without_package = [(5,[0])]
                               # # move_lines = [(5, 0), move_lines]
                               #
                               # # pick_output.action_assign()
                               # rec.picking_ids.shopify_id = fulfilment.shopify_fulfilment_id
                               # rec.picking_ids.action_confirm()
                               # rec.picking_ids.action_assign()
                               # test = rec.picking_ids.button_validate()
                               # if type(test) == dict and test.get('res_model') == 'stock.backorder.confirmation':
                               #     yy = self.env['stock.backorder.confirmation'].with_context(test.get('context')).process()
                               #     # yy.process()
                               # # else:
                               # #  pass


                           else:
                               backorder_picking = rec.picking_ids.filtered_domain([('backorder_id', "!=", False),('state','!=','done')])
                               self._process_picking(fulfilment, backorder_picking, rec)
                       else:
                           if picking_exist.state != 'done':
                               self._process_picking(fulfilment, picking_exist, rec)
                   except Exception as e:
                        rec.message_post(body="Exception-Order#{}-{}".format(rec.id, e.args))
                       # pass
                   # pass

               # if len(success_fulfilment) == 1 and success_fulfilment.shopify_fulfilment_status == 'fulfilled':
               #
               # elif len(success_fulfilment) >1:



class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    shopify_id = fields.Char(string="Shopify Id", readonly=True, store=True)
    marketplace_type = fields.Selection(
        [('shopify', 'Shopify')], string="Marketplace Type"
    )
