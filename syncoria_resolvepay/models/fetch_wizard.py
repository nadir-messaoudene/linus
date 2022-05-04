import logging
from dateutil import parser
from odoo import fields, models, exceptions, _
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(__name__)

class ResolvepayFetch(models.Model):
    _name = 'resolvepay.fetch'
    _description = 'Fetch Customer'

    instance_id = fields.Many2one(
        string='ResolvePay Instance',
        comodel_name='resolvepay.instance',
    )

    # date_from = fields.Date('From')
    # date_to = fields.Date('To')

    def fetch_customers_resolvepay(self):
        params = {'limit': 100, 'page': 1}
        url = self.instance_id.instance_baseurl + 'customers'
        res = self.instance_id.get_data(url, params)
        if res.get('data'):
            data = res.get('data')
            if data.get('count') > 0:
                customer_list = data.get('results')
                for customer in customer_list:
                    _logger.info("Customer info =====> %s", customer)
                    partner = self.env['res.partner'].search([('email', '=', customer.get('email'))], limit=1)
                    if partner:
                        partner.resolvepay_customer_id = customer.get('id')
                        partner.available_credit = customer.get('amount_available')
                        partner.advance_rate = customer.get('advance_rate')
                        partner.terms = customer.get('default_terms')
                        partner.net_terms_status = customer.get('net_terms_status')
                    else:
                        try:
                            partner_dict = {}
                            partner_dict['resolvepay_customer_id'] = customer.get('id')
                            partner_dict['street'] = customer.get('business_address')
                            partner_dict['city'] = customer.get('business_city')
                            state_id = self.env['res.country.state'].search([
                                ('code', '=', customer.get('business_state'))],
                                limit=1)
                            if state_id:
                                partner_dict['state_id'] = state_id.id
                            country_id = self.env['res.country'].search([
                                ('code', '=', customer.get('business_country'))],
                                limit=1)
                            if country_id:
                                partner_dict['country_id'] = country_id.id
                            partner_dict['zip'] = customer.get('business_zip')
                            partner_dict['email'] = customer.get('email')
                            partner_dict['phone'] = customer.get('business_ap_phone')
                            partner_dict['name'] = customer.get('business_name')
                            partner_dict['available_credit'] = customer.get('amount_available')
                            partner_dict['advance_rate'] = customer.get('advance_rate')
                            partner_dict['terms'] = customer.get('default_terms')
                            partner_dict['net_terms_status'] = customer.get('net_terms_status')
                            self.env['res.partner'].with_context(res_partner_search_mode='customer').create(partner_dict)
                        except Exception as e:
                            _logger.info("Error occurred =====> %s", e)
                            raise ValidationError('Error occurred: %s', e)

class ResolvepayFetchInvoice(models.Model):
    _name = 'resolvepay.fetch.invoice'
    _description = 'Fetch Invoice'

    instance_id = fields.Many2one(
        string='ResolvePay Instance',
        comodel_name='resolvepay.instance',
    )
    # date_from = fields.Date('From')
    # date_to = fields.Date('To')

    def fetch_invoices_resolvepay(self):
        url = self.instance_id.instance_baseurl + 'invoices'
        invoice_resolvepay_map = self.env['account.move'].search([('resolvepay_invoice_id', '!=', ''), ('payment_state', 'in', ['not_paid', 'partial'])])
        for invoice in invoice_resolvepay_map:
            complete_url = url + '/' + invoice.resolvepay_invoice_id
            res = self.instance_id.get_data(complete_url)
            if res.get('data'):
                data = res.get('data')
                _logger.info("Invoice data =====> %s", data)
                try:
                    if data.get('advanced'):
                        print(data.get('advanced_at'))
                        move_id = self.env['account.move'].search([('invoice_origin', '=', data.get('order_number')), ('move_type', "=", "out_invoice")])
                        journal = self.env['account.journal'].search([('code', '=', 'RSP')])
                        if journal and move_id and move_id == invoice:
                            payment_dict = {
                                'journal_id': journal.id,
                                'amount': data.get('amount_advance'),
                                'payment_date': data.get('advanced_at'),
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
                                    pmt_wizard = self.env['account.payment.register'].with_context(active_model='account.move',active_ids=move_id.ids).create(payment_dict)
                                    payment = pmt_wizard.action_create_payments()
                                    print("===============>", payment)
                    elif data.get('amount_paid'):
                        print(data.get('advanced_at'))
                        move_id = self.env['account.move'].search([('invoice_origin', '=', data.get('order_number')), ('move_type', "=", "out_invoice")])
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