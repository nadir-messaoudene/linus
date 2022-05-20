from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    threepl_customer_id = fields.Char(string='3PL Customer Id')