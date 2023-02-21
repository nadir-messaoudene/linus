import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _prepare_confirmation_values(self):
        return {
            'state': 'sale',
            'date_order': self._context.get('date_order') if self._context.get('date_order') else fields.Datetime.now()
        }

    lightspeed_sale_id = fields.Char(string='Lightspeed Sale Id', readonly=True)
    lightspeed_shop = fields.Many2one('lightspeed.shop', string='Lightspeed Shop', readonly=True)
    lightspeed_ticket_number = fields.Char(string='Lightspeed Ticket Number', readonly=True)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lightspeed_sale_line_id = fields.Char(string="Lightspeed SaleLine Id", readonly=True)
