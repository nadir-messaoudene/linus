import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    lightspeed_sale_id = fields.Char(string='Lightspeed Sale Id', readonly=True)
    lightspeed_ticket_number = fields.Char(string='Lightspeed Ticket Number', readonly=True)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    lightspeed_sale_id = fields.Char(string='Lightspeed Sale Id', readonly=True)
    lightspeed_ticket_number = fields.Char(string='Lightspeed Ticket Number', readonly=True)