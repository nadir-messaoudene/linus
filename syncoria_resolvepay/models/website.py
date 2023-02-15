from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
import json, time
from datetime import date
import logging
_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = 'website'

    def _prepare_sale_order_values(self, partner, pricelist):
        self.ensure_one()
        values = super()._prepare_sale_order_values(partner, pricelist)
        tag_id = self.env['crm.tag'].sudo().search([('name', '=', 'B2B')])
        if tag_id:
            values['tag_ids'] = [(4, tag_id.id)]
        return values

    @api.model
    def sale_get_payment_term(self, partner):
        pt = self.env.ref('account.account_payment_term_immediate', False).sudo()
        if pt:
            pt = (not pt.company_id.id or self.company_id.id == pt.company_id.id) and pt
        return (
                pt or
                self.env['account.payment.term'].sudo().search([('company_id', '=', self.company_id.id)], limit=1)
        ).id
