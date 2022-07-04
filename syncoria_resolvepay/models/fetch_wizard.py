import logging
from dateutil import parser
from odoo import fields, models, exceptions, _
from odoo.exceptions import UserError, ValidationError
_logger = logging.getLogger(__name__)
import time

class ResolvepayFetch(models.Model):
    _name = 'resolvepay.fetch'
    _description = 'Fetch Customer'

    instance_id = fields.Many2one(
        string='ResolvePay Instance',
        comodel_name='resolvepay.instance',
    )
    
    def fetch_customers_resolvepay(self):
        print("fetch_customers_resolvepay")
        instance = self.env['resolvepay.instance'].search([], limit=1)
        for i in range(1,130):
            params = {'limit': 100, 'page': i}
            url = instance.instance_baseurl + 'customers'
            res = instance.get_data(url, params)
            if res.get('data'):
                data = res.get('data')
                if data.get('count') > 0:
                    customer_list = data.get('results')
                    for customer in customer_list:
                        if customer.get('email') == None:
                            continue
                        #Check FOUND?
                        try:
                            time.sleep(0.5)
                            res = instance.get_data(url+"/"+customer.get('id'))
                        except:
                            continue
                        #END check FOUND?
                        partner = self.env['res.partner'].search([('email', '=', customer.get('email'))], limit=1)

                        if partner:
                            partner.resolvepay_customer_id = customer.get('id')
                            partner.available_credit = customer.get('amount_available')
                            partner.advance_rate = customer.get('advance_rate') * 100 if customer.get('advance_rate') else customer.get('advance_rate')
                            partner.terms = customer.get('default_terms').capitalize() if customer.get('default_terms') else customer.get('default_terms')
                            partner.net_terms_status = customer.get('net_terms_status').capitalize() if customer.get('net_terms_status') else customer.get('net_terms_status')
                            partner.credit_status = customer.get('credit_status').capitalize() if customer.get('credit_status') else customer.get('credit_status')
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
                                partner_dict['advance_rate'] = customer.get('advance_rate') * 100 if customer.get('advance_rate') else customer.get('advance_rate')
                                partner_dict['terms'] = customer.get('default_terms').capitalize() if customer.get('default_terms') else customer.get('default_terms')
                                partner_dict['net_terms_status'] = customer.get('net_terms_status').capitalize() if customer.get('net_terms_status') else customer.get('net_terms_status')
                                partner_dict['credit_status'] = customer.get('credit_status').capitalize() if customer.get('credit_status') else customer.get('credit_status')
                                self.env['res.partner'].with_context(res_partner_search_mode='customer').create(partner_dict)
                            except Exception as e:
                                _logger.info("Error occurred =====> %s", e)
                                raise ValidationError('Error occurred: %s', e)
        _logger.info("Complete===>>>fetch_customers_resolvepay")
    

class ResolvepayFetchInvoice(models.Model):
    _name = 'resolvepay.fetch.invoice'
    _description = 'Fetch Invoice'

    instance_id = fields.Many2one(
        string='ResolvePay Instance',
        comodel_name='resolvepay.instance',
    )

    def fetch_invoices_resolvepay(self):
        invoice_resolvepay_map = self.env['account.move'].search([('resolvepay_invoice_id', '!=', ''), ('payment_state', 'in', ['not_paid', 'partial', 'in_payment']), ('move_type', '=', 'out_invoice')])
        for invoice in invoice_resolvepay_map:
            invoice.resolvepay_fetch_invoice()