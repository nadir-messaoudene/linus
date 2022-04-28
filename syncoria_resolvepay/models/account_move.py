from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
import json

class Invoice(models.Model):
    _inherit = 'account.move'

    resolvepay_invoice_id = fields.Char(string='ResolvePay Invoice Id')