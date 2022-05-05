from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
import json
import logging
_logger = logging.getLogger(__name__)

class Invoice(models.Model):
    _inherit = 'account.move'

    resolvepay_invoice_id = fields.Char(string='ResolvePay Invoice Id')

    def create_invoice_resolvepay(self):
        print('create_invoice_resolvepay')
        sale_order = self.env['sale.order'].search([('name', '=', self.invoice_origin)])
        if not sale_order:
            raise UserError('This invoice does not belong to any order')
        tag = sale_order.tag_ids.search([('name', '=', 'B2B')])
        if not tag:
            raise UserError('The order that produced this invoice does not have tag B2B')
        if self.resolvepay_invoice_id:
            raise UserError('This invoice is already exported. ResolvepayId: ' + self.resolvepay_invoice_id)
        resolvepay_instance = self.env['resolvepay.instance'].search([('name', '=', 'ResolvePay')])
        if len(resolvepay_instance):
            url = resolvepay_instance.instance_baseurl + 'invoices'
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            invoice_url = base_url + '/my/invoices/' + str(self.id)
            print(invoice_url)
            if not self.partner_id.resolvepay_customer_id:
                raise ValidationError('This customer does not exist in ResolvePay')
            invoice_data = dict(
                amount=self.amount_total,
                customer_id=self.partner_id.resolvepay_customer_id,
                number=self.name,
                order_number=self.invoice_origin,
                merchant_invoice_url=invoice_url
            )
            res = resolvepay_instance.post_data(url=url, data=json.dumps(invoice_data))
            if res.get('data'):
                data = res.get('data')
                self.message_post(
                    body="Export to ResolvePay successfully. ResolvePay Invoice ID: {}".format(data.get('id')))
                self.resolvepay_invoice_id = data.get('id')
        else:
            raise UserError('There is no ResolvePay instance')

    def resolvepay_fetch_invoice(self):
        for invoice in self:
            resolvepay_instance = self.env['resolvepay.instance'].search([('name', '=', 'ResolvePay')])
            url = resolvepay_instance.instance_baseurl + 'invoices'
            complete_url = url + '/' + invoice.resolvepay_invoice_id
            res = self.instance_id.get_data(complete_url)
            if res.get('data'):
                data = res.get('data')
                _logger.info("Invoice data =====> %s", data)
                try:
                    if data.get('amount_refunded'):
                        pass
                    elif data.get('advanced'):
                        print(data.get('advanced_at'))
                        move_id = self.env['account.move'].search(
                            [('invoice_origin', '=', data.get('order_number')), ('move_type', "=", "out_invoice")])
                        journal = self.env['account.journal'].search([('code', '=', 'RSP')])
                        if journal and move_id and move_id == invoice:
                            payment_dict = {
                                'journal_id': journal.id,
                                'amount': data.get('amount_advance'),
                                'payment_date': data.get('updated_at'),
                                'partner_id': invoice.partner_id.id,
                                'resolvepay_payment_date': data.get('updated_at')
                            }
                            payment_method_line_id = journal.inbound_payment_method_line_ids
                            if payment_method_line_id:
                                payment_dict['payment_method_line_id'] = payment_method_line_id.id
                            domain = []
                            for move in move_id:
                                domain += [('ref', '=', move.name)]
                            if domain:
                                pay_id = self.env['account.payment'].search(domain, order='id desc', limit=1)
                                if pay_id:
                                    if pay_id.resolvepay_payment_date != data.get('updated_at'):
                                        payment_dict['communication'] = pay_id.ref.split('-')[0]
                                        pmt_wizard = self.env['account.payment.register'].with_context(
                                            active_model='account.move', active_ids=move_id.ids).create(payment_dict)
                                        payment = pmt_wizard.action_create_payments()
                                        print("===============>", payment)
                                else:
                                    pmt_wizard = self.env['account.payment.register'].with_context(
                                        active_model='account.move', active_ids=move_id.ids).create(payment_dict)
                                    payment = pmt_wizard.action_create_payments()
                                    print("===============>", payment)
                    elif data.get('amount_paid'):
                        print(data.get('advanced_at'))
                        move_id = self.env['account.move'].search(
                            [('invoice_origin', '=', data.get('order_number')), ('move_type', "=", "out_invoice")])
                        journal = self.env['account.journal'].search([('code', '=', 'RSP')])
                        if journal and move_id and move_id == invoice:
                            payment_dict = {
                                'journal_id': journal.id,
                                'amount': data.get('amount_paid'),
                                'payment_date': data.get('updated_at'),
                                'partner_id': invoice.partner_id.id,
                                'resolvepay_payment_date': data.get('updated_at')
                            }
                            payment_method_line_id = journal.inbound_payment_method_line_ids
                            if payment_method_line_id:
                                payment_dict['payment_method_line_id'] = payment_method_line_id.id
                            domain = []
                            for move in move_id:
                                domain += [('ref', '=', move.name)]
                            if domain:
                                pay_id = self.env['account.payment'].search(domain, order='id desc', limit=1)
                                if pay_id:
                                    if pay_id.resolvepay_payment_date != data.get('updated_at'):
                                        payment_dict['communication'] = pay_id.ref.split('-')[0]
                                        pmt_wizard = self.env['account.payment.register'].with_context(
                                            active_model='account.move', active_ids=move_id.ids).create(payment_dict)
                                        payment = pmt_wizard.action_create_payments()
                                        print("===============>", payment)
                                else:
                                    pmt_wizard = self.env['account.payment.register'].with_context(
                                        active_model='account.move', active_ids=move_id.ids).create(payment_dict)
                                    payment = pmt_wizard.action_create_payments()
                                    print("===============>", payment)
                except Exception as e:
                    _logger.warning("Exception-{}".format(e))
                    raise ValidationError(e)