import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "product.product"

    lightspeed_item_id = fields.Char(string='Lightspeed Item ID')