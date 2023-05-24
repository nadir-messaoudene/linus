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
    fetch_type = fields.Selection([('date', 'Date Range'), ('id', 'ID'), ('all', 'All')], default='date', string="Operation Type")
    order_type = fields.Selection([('all', 'All'), ('completed', 'Completed')], default='completed', string="Order Type")
    instance_id = fields.Many2one(string='Lightspeed Instance', comodel_name='lightspeed.instance')

    date_from = fields.Datetime('From')
    date_to = fields.Datetime('To')
    id_to_fetch = fields.Integer('ID')
    ticket_number = fields.Char('Ticket Number')

    def lightspeed_fetch_objects(self):
        kwargs = dict(
            date_from=self.date_from,
            date_to=self.date_to,
            id_to_fetch=self.id_to_fetch,
            ticket_number=self.ticket_number
        )
        if self.object_to_fetch == 'order':
            kwargs['completed'] = True if self.order_type == 'completed' else False
            return self.instance_id.fetch_orders(kwargs)
        elif self.object_to_fetch == 'customer':
            return self.instance_id.fetch_customers(kwargs)
