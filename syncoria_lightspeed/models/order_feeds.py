import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class LightspeedOrderFeeds(models.Model):
    _name = 'lightspeed.order.feeds'
    _description = 'Lightspeed Order Feeds'

    _order = 'name DESC'

    name = fields.Char(string='Name', required=True, copy=False)
    instance_id = fields.Many2one(
        string='Lightspeed Instance',
        comodel_name='lightspeed.instance',
        ondelete='restrict',
    )
    order_data = fields.Text(readonly=1)
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('done', 'Done'),
                   ('error', 'Error')]
    )
