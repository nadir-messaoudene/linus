from odoo import models, fields
import requests, json
from requests.auth import HTTPBasicAuth
from odoo.exceptions import UserError

class Carrier3PL(models.Model):
    _name = 'carriers.3pl'
    _description = "Carrier 3PL"

    name = fields.Char(string='Name', required=True)
    
    instance_3pl_id = fields.Many2one('instance.3pl', 'Instance')
    service_ids = fields.One2many('carrier.services.3pl', 'carrier_3pl_id', string='Carriers')
    customer_account_ids = fields.One2many('carriers.3pl.customer.account', 'carrier_3pl_id', string='Customer Accounts')

class CarrierServices3PL(models.Model):
    _name = 'carrier.services.3pl'
    _description = 'Carrier Services 3PL'

    name = fields.Char(string='Description', required=True)
    code = fields.Char(string='Code', required=True)
    shipEngineId = fields.Char(string='Ship Engine Id')
    carrier_3pl_id = fields.Many2one('carriers.3pl', 'Carrier', ondelete='cascade')

class Carrier3PLCustomerAccount(models.Model):
    _name = 'carriers.3pl.customer.account'
    _description = "Carrier 3PL Customer Account"
    _order = "partner_id"

    name = fields.Char(string='Account Number')
    partner_id = fields.Many2one('res.partner', 'Customer')
    carrier_3pl_id = fields.Many2one('carriers.3pl', 'Carrier', ondelete='cascade')
    is_default = fields.Boolean('Default', default=False)

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.partner_id:
                name = name + ' (' + record.partner_id.name + ')'
            else:
                name = name + ' (Default)'
            result.append((record.id, name))
        return result