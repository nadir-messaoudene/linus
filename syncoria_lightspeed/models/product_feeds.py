import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class LightspeedProductFeeds(models.Model):
    _name = 'lightspeed.product.feeds'
    _description = 'Lightspeed Product Feeds'

    name = fields.Char(string='Name', required=True)
    instance_id = fields.Many2one(
        string='Lightspeed Instance',
        comodel_name='lightspeed.instance',
        ondelete='restrict',
    )
    product_data = fields.Text(readonly=1)
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('done', 'Done'),
                   ('error', 'Error')]
    )
