import logging
import datetime
from odoo import fields, models, exceptions, _
logger = logging.getLogger(__name__)

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
        pass