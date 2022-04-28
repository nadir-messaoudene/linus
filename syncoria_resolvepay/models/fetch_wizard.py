import logging
import datetime
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
    date_from = fields.Date('From')
    date_to = fields.Date('To')

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
                        if not partner.resolvepay_customer_id:
                            partner.resolvepay_customer_id = customer.get('id')
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
                            self.env['res.partner'].create(partner_dict)
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
    date_from = fields.Date('From')
    date_to = fields.Date('To')

    def fetch_invoices_resolvepay(self):
        params = {'limit': 100, 'page': 1}
        url = self.instance_id.instance_baseurl + 'invoices'
        res = self.instance_id.get_data(url, params)
        if res.get('data'):
            data = res.get('data')
            if data.get('count') > 0:
                invoice_list = data.get('results')
                for invoice in invoice_list:
                    _logger.info("Invoice info =====> %s", invoice)
