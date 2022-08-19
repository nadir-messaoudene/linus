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
    customer_data = fields.Text(readonly=1)
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('done', 'Done'),
                   ('error', 'Error')]
    )
    lightspeed_customer_id = fields.Char(string='Customer ID')
    first_name = fiels.Char(string='First Name')
    last_name = fiels.Char(string='Last Name')
    company = fields.Char(string='Company')
    vat_number = fields.Char(string='VAT Number')
    lightspeed_contact_id = fields.Char(string='Contact ID')
    address = fields.Char(string='Address')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    state_code = fields.Char(string='State Code')
    zip = fields.Char(string='Zip')
    country = fields.Char(string='Country')
    country_code = fields.Char(string='Country Code')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
