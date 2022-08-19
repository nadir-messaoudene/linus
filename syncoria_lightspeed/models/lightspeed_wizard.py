from email.policy import default
from odoo import api,fields, models
import requests
import json
from odoo.exceptions import AccessError, UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class FetchWizard(models.TransientModel):
    _name = 'lightspeed.fetch.wizard'
    _description = 'Lightspeed Fetch Wizard'

    object_to_fetch = fields.Selection([('order', 'Order'), ('product', 'Product'), ('customer', 'Customer')], default='order', string="Object")
    fetch_type = fields.Selection([('date', 'Date Range'), ('id', 'ID')], default='date', string="Operation Type")

    instance_id = fields.Many2one(string='Lightspeed Instance', comodel_name='lightspeed.instance')

    date_from = fields.Datetime('From')
    date_to = fields.Datetime('To')

    def lightspeed_fetch_orders(self):
        self.instance_id.fetch_orders(self.date_from, self.date_to)
