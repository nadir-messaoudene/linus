from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
import json, time
from datetime import date
import logging
_logger = logging.getLogger(__name__)

class Invoice(models.Model):
    _inherit = 'account.move'

    resolvepay_invoice_id = fields.Char(string='ResolvePay Invoice Id')
    resolvepay_charge_id = fields.Char(string='ResolvePay Charge Id')
    available_credit = fields.Integer(string='Available Credit', related='partner_id.available_credit')

    payout_transaction_ids = fields.One2many(comodel_name='resolvepay.payout.transaction', inverse_name='move_id', string='Payout Transaction')
    # def action_update_resolve_pay(self):
    #     to_update = self.env['account.move'].search([('resolvepay_invoice_id', '!=', None), ('state', '=', 'posted'), ('payment_state', 'in', ('not_paid', 'in_payment', 'partial'))])
    #     _logger.info("Invoices info =====> %s", to_update)
    #     if not to_update:
    #         return
    #     for rec in to_update:
    #         try:
    #             time.sleep(0.5)
    #             rec.resolvepay_fetch_invoice()
    #         except:
    #             continue

    def action_update_resolve_pay(self):
        date_params_start = fields.Datetime.now().strftime("%Y-%m-%dT00:00:00.000Z")
        date_params_end = fields.Datetime.now().strftime("%Y-%m-%dT23:59:59.000Z")
        today_date = fields.Date.today()
        resolvepay_instance = self.env['resolvepay.instance'].search([('name', '=', 'ResolvePay')])
        url = resolvepay_instance.instance_baseurl + 'payouts'
        complete_url = url + '?filter[expected_by][gte]=' + date_params_start + '&filter[expected_by][lte]=' + date_params_end + '&status=paid'
        res = resolvepay_instance.get_data(complete_url)
        _logger.info(res)
        payouts = res.get('data').get('results')
        for payout in payouts:
            _logger.info(payout)
            if payout.get('status') != 'paid':
                continue
            payment_date = payout.get('expected_by')
            payout_id = payout.get('id')
            url = resolvepay_instance.instance_baseurl + 'payout-transactions?filter[payout_id]=' + payout_id
            res = resolvepay_instance.get_data(url)
            if res.get('data'):
                payout_transactions = res.get('data').get('results')
                for payout_transaction in payout_transactions:
                    _logger.info(payout_transaction)
                    invoice_id = payout_transaction.get('invoice_id', False)
                    invoice = self.search([('resolvepay_invoice_id', '=', invoice_id)], limit=1)
                    if not invoice:
                        _logger.info('Cannot find RP invoice: ' + invoice_id)
                    if invoice.state == 'posted' and invoice.payment_state in ('partial', 'not_paid'):
                        self.register_resolvepay_payment(invoice, payout_transaction, payment_date)
                    self.create_payout_transaction(invoice, payout_transaction)

    def create_invoice_resolvepay(self):
        for record in self:
            if record.state != 'posted':
                raise UserError('This invoice is in draft mode')
            sale_order = self.env['sale.order'].search([('name', '=', record.invoice_origin)])
            if not sale_order:
                raise UserError('This invoice does not belong to any order')
            tag = sale_order.tag_ids.search([('name', '=', 'B2B')])
            if not tag:
                raise UserError('The order that produced this invoice does not have tag B2B')
            if record.resolvepay_invoice_id:
                raise UserError('This invoice is already exported. ResolvepayId: ' + record.resolvepay_invoice_id)
            resolvepay_instance = self.env['resolvepay.instance'].search([('name', '=', 'ResolvePay')])
            if len(resolvepay_instance):
                url = resolvepay_instance.instance_baseurl + 'invoices'
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                invoice_url = base_url + '/my/invoices/' + str(record.id)
                print(invoice_url)
                resolvepay_customer = False
                resolvepay_customer_id = False
                if record.partner_id.resolvepay_customer_id:
                    resolvepay_customer = True
                    resolvepay_customer_id = record.partner_id.resolvepay_customer_id
                elif record.partner_id.parent_id:
                    if record.partner_id.parent_id.resolvepay_customer_id:
                        resolvepay_customer = True
                        resolvepay_customer_id = record.partner_id.parent_id.resolvepay_customer_id
                if not resolvepay_customer:
                    raise ValidationError('This customer does not exist in ResolvePay')
                invoice_data = dict(
                    amount=record.amount_total,
                    customer_id=resolvepay_customer_id,
                    number=record.name,
                    order_number=record.invoice_origin,
                    merchant_invoice_url=invoice_url
                )
                res = resolvepay_instance.post_data(url=url, data=json.dumps(invoice_data))
                if res.get('data'):
                    data = res.get('data')
                    record.message_post(
                        body="Export to ResolvePay successfully. ResolvePay Invoice ID: {}".format(data.get('id')))
                    record.resolvepay_invoice_id = data.get('id')
            else:
                raise UserError('There is no ResolvePay instance')

    def get_payout_info(self, payout_id):
        resolvepay_instance = self.env['resolvepay.instance'].search([('name', '=', 'ResolvePay')])
        url = resolvepay_instance.instance_baseurl + 'payouts/' + payout_id
        res = resolvepay_instance.get_data(url)
        return res.get('data')

    def register_resolvepay_payment(self, invoice, payout_transaction, arrive_date):
        payout_transaction_id = payout_transaction.get('id')
        payout_id = payout_transaction.get('payout_id')
        amount_gross = payout_transaction.get('amount_gross')
        amount_fee = payout_transaction.get('amount_fee')
        amount_net = payout_transaction.get('amount_net')
        payment_type = payout_transaction.get('type')
        invoice_id = payout_transaction.get('invoice_id', False)
        payment_id = self.env['account.payment'].search([('rp_payout_transaction_id', '=', payout_transaction_id)])
        if payment_id:
            return
        if payment_type not in ('advance', 'payment'):
            return
        if amount_gross > invoice.amount_residual:
            return
        if invoice_id == invoice.resolvepay_invoice_id and invoice.payment_state in ('not_paid', 'partial'):
            journal = self.env['account.journal'].search([('code', '=', 'RSP')])
            if not journal:
                raise ValidationError('Can not find Resolve Pay journal')
            payment_dict = {
                'journal_id': journal.id,
                'amount': amount_gross,
                'payment_date': arrive_date,
            }
            payment_method_line_id = journal.inbound_payment_method_line_ids
            if payment_method_line_id:
                payment_dict['payment_method_line_id'] = payment_method_line_id[0].id
                pmt_wizard = self.env['account.payment.register'].with_context(
                    active_model='account.move', active_ids=invoice.ids).create(payment_dict)
                new_payment_id = pmt_wizard._create_payments()
                new_payment_id.write({'rp_payout_transaction_id': payout_transaction_id,
                                      'rp_payout_id': payout_id,
                                      'rp_payout_transaction_type': payment_type,
                                      'rp_payout_transaction_amount_gross': amount_gross,
                                      'rp_payout_transaction_amount_fee': amount_fee,
                                      'rp_payout_transaction_amount_net': amount_net})

    def resolvepay_fetch_invoice(self):
        for invoice in self:
            if invoice.state == 'cancel':
                continue
            if invoice.state == 'draft':
                raise UserError('This invoice is not confirmed '+invoice.name)
            resolvepay_instance = self.env['resolvepay.instance'].search([('name', '=', 'ResolvePay')])
            url = resolvepay_instance.instance_baseurl + 'payout-transactions?filter[invoice_id]='
            complete_url = url + invoice.resolvepay_invoice_id
            res = resolvepay_instance.get_data(complete_url)
            if res.get('data').get('results'):
                data = res.get('data').get('results', [])
                _logger.info("Payout Transactions data =====> %s", data)
                try:
                    for payout_transaction in data:
                        _logger.info(payout_transaction)
                        payout_id = payout_transaction.get('payout_id')
                        payout_info = self.get_payout_info(payout_id)
                        if payout_info.get('status') != 'paid':
                            return
                        payout_arrive_date = payout_info.get('expected_by')
                        self.register_resolvepay_payment(invoice, payout_transaction, payout_arrive_date)
                        self.create_payout_transaction(self, payout_transaction)
                except Exception as e:
                    _logger.info("Exception-{}".format(e))
                    raise ValidationError(e)

    def create_payout_transaction(self, invoice, payout_transaction):
        payout_transaction_field = self.env['resolvepay.payout.transaction']._fields
        val_dict = {}
        for key, value in payout_transaction.items():
            val_dict['transaction_'+key] = value
        val_dict['move_id'] = invoice.id
        _logger.info(val_dict)
        payout_transaction_id = self.env['resolvepay.payout.transaction'].search([('transaction_id', '=', val_dict['transaction_id'])])
        if not payout_transaction_id:
            self.env['resolvepay.payout.transaction'].create(val_dict)