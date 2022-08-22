import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class LightspeedCustomerFeeds(models.Model):
    _name = 'lightspeed.customer.feeds'
    _description = 'Lightspeed Customer Feeds'

    _order = 'name DESC'

    name = fields.Char(string='Name', required=True)
    instance_id = fields.Many2one(
        string='Lightspeed Instance',
        comodel_name='lightspeed.instance',
        ondelete='restrict',
    )
    customer_data = fields.Text(string='Customer Data',readonly=1)
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('done', 'Done'),
                   ('error', 'Error')],
        default='draft'
    )
    lightspeed_customer_id = fields.Char(string='Customer ID')
    first_name = fields.Char(string='First Name')
    last_name = fields.Char(string='Last Name')
    company = fields.Char(string='Company')
    vat_number = fields.Char(string='VAT Number')
    lightspeed_contact_id = fields.Char(string='Contact ID')
    street1 = fields.Char(string='Address 1')
    street2 = fields.Char(string='Address 2')
    city = fields.Char(string='City')
    state_name = fields.Char(string='State')
    state_code = fields.Char(string='State Code')
    zip = fields.Char(string='Zip')
    country = fields.Char(string='Country')
    country_code = fields.Char(string='Country Code')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')
    message = fields.Text(string='Logging')

    def create_feeds(self, customer_list):
        for customer in customer_list:
            try:
                feed = self.create_feed(customer)
                self += feed
            except Exception as e:
                continue
        return self

    def create_feed(self, customer):
        try:
            _logger.info('Start creating/updating feeds for customer: {} {}'.format(customer.get('firstName'), customer.get('lastName')))
            contact = customer.get('Contact')
            addresses = contact.get('Addresses').get('ContactAddress')
            vals = {
                'name': customer.get('firstName') + " " + customer.get('lastName'),
                'instance_id': self.env.context.get('instance_id').id,
                'customer_data': customer,
                'lightspeed_customer_id': customer.get('customerID'),
                'first_name': customer.get('firstName'),
                'last_name': customer.get('lastName'),
                'company': customer.get('company'),
                'vat_number': customer.get('vatNumber'),
                'lightspeed_contact_id': customer.get('contactID'),
                'street1': addresses.get('address1'),
                'street2': addresses.get('address2'),
                'city': addresses.get('city'),
                'state_name': addresses.get('state'),
                'state_code': addresses.get('stateCode'),
                'zip': addresses.get('zip'),
                'country': addresses.get('country'),
                'country_code': addresses.get('countryCode'),
                'message': '',
                'state': 'draft'
            }
            if contact.get('Phones') != '':
                phones = contact.get('Phones').get('ContactPhone')
                if type(phones) is dict:
                    phones = [phones]
                for phone in phones:
                    if phone.get('useType') == 'Home':
                        vals['phone'] = phone.get('number')
                    if phone.get('useType') == 'Mobile':
                        vals['mobile'] = phone.get('number')
            if contact.get('Emails') != '':
                emails = contact.get('Emails').get('ContactEmail')
                if type(emails) is dict:
                    emails = [emails]
                for email in emails:
                    if email.get('useType') == 'Primary':
                        vals['email'] = email.get('address')
            if contact.get('Websites') != '':
                vals['website'] = contact.get('Websites').get('ContactWebsite').get('url')
            _logger.info(vals)
            customer_feed_id = self.search([('lightspeed_customer_id', '=', customer.get('customerID'))])
            if customer_feed_id:
                customer_feed_id.write(vals)
            else:
                customer_feed_id = self.create(vals)
            return customer_feed_id
        except Exception as e:
            self.state = 'error'
            self.message = e
            _logger.info(e)
            raise ValidationError(e)

    def evaluate_feed(self):
        _logger.info(self)
        for feed in self:
            _logger.info('Start evaluating feeds for customer: {}'.format(feed.name))

