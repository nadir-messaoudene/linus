from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
import json, time
import logging
_logger = logging.getLogger(__name__)

class Invoice(models.Model):
    _inherit = 'account.move'

    resolvepay_invoice_id = fields.Char(string='ResolvePay Invoice Id')
    resolvepay_charge_id = fields.Char(string='ResolvePay Charge Id')
    available_credit = fields.Integer(string='Available Credit', related='partner_id.available_credit')

    def action_update_resolve_pay(self):
        to_update = self.env['account.move'].search([('resolvepay_invoice_id', '!=', None), ('state', '=', 'posted'), ('payment_state', 'in', ('not_paid', 'in_payment', 'partial'))])
        print("to_update")
        print(to_update)
        if not to_update:
            return
        for rec in to_update:
            try:
                time.sleep(0.5)
                rec.resolvepay_fetch_invoice()
            except:
                continue

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
                if not record.partner_id.resolvepay_customer_id:
                    raise ValidationError('This customer does not exist in ResolvePay')
                invoice_data = dict(
                    amount=record.amount_total,
                    customer_id=record.partner_id.resolvepay_customer_id,
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

    def resolvepay_fetch_invoice(self):
        for invoice in self:
            if self.state != 'posted':
                raise UserError('This invoice is not confirmed'+self.name)
            resolvepay_instance = self.env['resolvepay.instance'].search([('name', '=', 'ResolvePay')])
            url = resolvepay_instance.instance_baseurl + 'invoices'
            complete_url = url + '/' + invoice.resolvepay_invoice_id
            res = resolvepay_instance.get_data(complete_url)
            if res.get('data'):
                data = res.get('data')
                _logger.info("Invoice data =====> %s", data)
                try:
                    if data.get('advanced'):
                        move_id = self.env['account.move'].search(
                            [('invoice_origin', '=', data.get('order_number')), ('move_type', "=", "out_invoice")])
                        if not move_id:
                            move_id = self.env['account.move'].search([('name', '=', data.get('number'))])
                        journal = self.env['account.journal'].search([('code', '=', 'RSP')])
                        if not journal:
                            raise ValidationError('Can not find Resolve Pay journal')
                        if journal and move_id and move_id == invoice:
                            payment_dict = {
                                'journal_id': journal.id,
                                'amount': data.get('amount_advance'),
                                'payment_date': data.get('advanced_at'),
                                'partner_id': invoice.partner_id.id,
                                'resolvepay_payment_date': data.get('advanced_at')
                            }
                            payment_method_line_id = journal.inbound_payment_method_line_ids
                            if payment_method_line_id:
                                payment_dict['payment_method_line_id'] = payment_method_line_id.id
                            domain = []
                            for move in move_id:
                                domain += [('ref', '=', move.name)]
                            if domain:
                                pay_id = self.env['account.payment'].search(domain, order='id desc', limit=1)
                                if not pay_id:
                                    pmt_wizard = self.env['account.payment.register'].with_context(
                                        active_model='account.move', active_ids=move_id.ids).create(payment_dict)
                                    payment = pmt_wizard.action_create_payments()
                                    print("===============>", payment)
                                    _logger.info(
                                        "Payment-{} Posted for Invoice-{}".format(payment, invoice))
                                    invoice.partner_id.fetch_customer_resolvepay()
                    if data.get('amount_paid'):
                        move_id = self.env['account.move'].search(
                            [('invoice_origin', '=', data.get('order_number')), ('move_type', "=", "out_invoice")])
                        if not move_id:
                            move_id = self.env['account.move'].search([('name', '=', data.get('number'))])
                        journal = self.env['account.journal'].search([('code', '=', 'RSP')])
                        if not journal:
                            raise ValidationError('Can not find Resolve Pay journal')
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
                                pay_ids = self.env['account.payment'].search(domain)
                                if pay_id:
                                    total_amount = 0
                                    for pay in pay_ids:
                                        total_amount += pay.amount
                                    if data.get('amount_paid') > total_amount:
                                        payment_dict['communication'] = pay_id.ref.split('-')[0]
                                        payment_dict['amount'] = data.get('amount_paid') - total_amount
                                        pmt_wizard = self.env['account.payment.register'].with_context(
                                            active_model='account.move', active_ids=move_id.ids).create(payment_dict)
                                        payment = pmt_wizard.action_create_payments()
                                        print("===============>", payment)
                                        _logger.info(
                                            "Payment-{} Posted for Invoice-{}".format(payment, invoice))
                                        invoice.partner_id.fetch_customer_resolvepay()
                                else:
                                    pmt_wizard = self.env['account.payment.register'].with_context(
                                        active_model='account.move', active_ids=move_id.ids).create(payment_dict)
                                    payment = pmt_wizard.action_create_payments()
                                    print("===============>", payment)
                                    _logger.info(
                                        "Payment-{} Posted for Invoice-{}".format(payment, invoice))
                                    invoice.partner_id.fetch_customer_resolvepay()
                    if data.get('amount_refunded'):
                        move_id = self.env['account.move'].search(
                            [('invoice_origin', '=', data.get('order_number')), ('move_type', "=", "out_invoice")])
                        if not move_id:
                            move_id = self.env['account.move'].search([('name', '=', data.get('number'))])
                        refund_move_id = self.env['account.move'].search(
                            [('invoice_origin', '=', data.get('order_number')), ('move_type', "=", "out_refund")])
                        if move_id != invoice:
                            raise ValidationError("Invoice Resolve Pay-{} is different from Invoice Odoo-{}".format(move_id, invoice))
                        if move_id == invoice and move_id.payment_state in ['paid', 'in_payment', 'partial']:
                            journal = self.env['account.journal'].search([('code', '=', 'RSP')])
                            if not refund_move_id:
                                wizard_vals = {
                                    'refund_method': 'refund',
                                    'date': data.get('updated_at'),
                                    'journal_id': invoice.journal_id.id
                                }
                                reversal_wizard = self.env['account.move.reversal'].with_context(
                                    active_model='account.move',
                                    active_ids=move_id.ids).create(wizard_vals)
                                reversal_wizard.sudo().reverse_moves()
                                refund_move_id = self.env['account.move'].search(
                                    [('invoice_origin', '=', data.get('order_number')), ('move_type', "=", "out_refund")])
                                if not refund_move_id:
                                    refund_move_id = self.env['account.move'].search(
                                        [('invoice_origin', '=', move_id.invoice_origin),
                                         ('move_type', "=", "out_refund")])
                                refund_move_id.resolvepay_invoice_id = ''
                                refund_move_id.invoice_line_ids.with_context(check_move_validity=False).unlink()
                                refund_move_id.invoice_line_ids = [(0, 0, {'move_id': refund_move_id.id,
                                                                       'name': "Refund",
                                                                       'quantity': 1,
                                                                       'price_unit': data.get('amount_refunded')})]
                            else:
                                total_refund = 0
                                for refund in refund_move_id:
                                    total_refund += refund.amount_total
                                if data.get('amount_refunded') > total_refund:
                                    wizard_vals = {
                                        'refund_method': 'refund',
                                        'date': data.get('updated_at'),
                                        'journal_id': invoice.journal_id.id
                                    }
                                    reversal_wizard = self.env['account.move.reversal'].with_context(
                                        active_model='account.move',
                                        active_ids=move_id.ids).create(wizard_vals)
                                    reversal_wizard.sudo().reverse_moves()
                                    refund_move_id = self.env['account.move'].search(
                                        [('invoice_origin', '=', data.get('order_number')),
                                         ('move_type', "=", "out_refund")], order='id desc', limit=1)
                                    refund_move_id.resolvepay_invoice_id = ''
                                    refund_move_id.invoice_line_ids.with_context(check_move_validity=False).unlink()
                                    refund_move_id.invoice_line_ids = [(0,0, {'move_id': refund_move_id.id,
                                                                           'name': "Refund",
                                                                           'quantity': 1,
                                                                           'price_unit': data.get('amount_refunded') - total_refund})]
                            if refund_move_id and refund_move_id.state != 'posted':
                                refund_move_id.action_post()
                                _logger.info("Credit Note-{} Posted for Invoice-{}".format(refund_move_id, invoice))
                            if not journal:
                                raise ValidationError('Can not find Resolve Pay journal')
                            if journal and refund_move_id:
                                payment_dict = {
                                    'journal_id': journal.id,
                                    'amount': refund_move_id.amount_total,
                                    'payment_date': data.get('updated_at'),
                                }
                                payment_method_line_id = journal.outbound_payment_method_line_ids
                                if payment_method_line_id:
                                    payment_dict['payment_method_line_id'] = payment_method_line_id[0].id
                                pmt_wizard = self.env['account.payment.register'].with_context(
                                    active_model='account.move', active_ids=refund_move_id.ids).create(
                                    payment_dict)
                                payment = pmt_wizard.action_create_payments()
                                print("===============>", payment)
                                _logger.info(
                                    "Payment-{} Posted for Credit Note-{}".format(payment, refund_move_id))
                except Exception as e:
                    _logger.info("Exception-{}".format(e))
                    raise ValidationError(e)