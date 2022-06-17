from odoo import models, fields


class UnitOfMeasureTypes(models.Model):
    _name = 'measure.types'

    name = fields.Char(string='Name', required=True)
    instance_3pl_id = fields.Many2one('instance.3pl', 'Instance')
