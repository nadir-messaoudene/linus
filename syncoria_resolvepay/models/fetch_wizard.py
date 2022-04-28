import logging
import datetime
from odoo import fields, models, exceptions, _
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
                    if partner and not partner.resolvepay_customer_id:
                        partner.resolvepay_customer_id = customer.get('id')
                    else:
                        # self.env['res.partner'].create()
                        print('else')
