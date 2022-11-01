# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from functools import partial
from itertools import count, groupby
import json

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.osv import expression
from odoo.tools import float_is_zero, html_keep_url, is_html_empty


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_status = fields.Selection([
        ('none', ''),
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('push_3pl', 'Pushed to 3PL'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
        ], string='Delivery Status', default='none', compute='_action_get_delivery', store=True)
    count_backorder = fields.Integer('Back Orders Count', compute='_action_get_delivery', store=True)

    last_carrier_tracking_ref = fields.Char(string='Tracking Reference', compute='_action_get_delivery', store=True)

    @api.depends('picking_ids.carrier_tracking_ref', 'picking_ids.state')
    def _action_get_delivery(self):
        for order in self:
            pickings = order.picking_ids.filtered(lambda l: l.picking_type_id.code != 'internal')
            backorders = pickings.backorder_ids.filtered(lambda l: l.state not in ('done', 'cancel'))
            order.count_backorder = len(backorders)

            if len(pickings) > 0:
                order.last_carrier_tracking_ref = pickings[-1].carrier_tracking_ref
                order.delivery_status = pickings[-1].state
            else: 
                order.last_carrier_tracking_ref = ''
                order.delivery_status = 'none'

    def action_update(self):
        to_update = self.env['sale.order'].search([])
        if not to_update:
            return
        for rec in to_update:
            rec._action_get_delivery()

    #Override for disable auto fill pricelist_id field
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'fiscal_position_id': False,
            })
            return

        self = self.with_company(self.company_id)

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        values = {
            # 'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        user_id = partner_user.id
        if not self.env.context.get('not_self_saleperson'):
            user_id = user_id or self.env.context.get('default_user_id', self.env.uid)
        if user_id and self.user_id.id != user_id:
            values['user_id'] = user_id

        if self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms'):
            if self.terms_type == 'html' and self.env.company.invoice_terms_html:
                baseurl = html_keep_url(self.get_base_url() + '/terms')
                values['note'] = _('Terms & Conditions: %s', baseurl)
            elif not is_html_empty(self.env.company.invoice_terms):
                values['note'] = self.with_context(lang=self.partner_id.lang).env.company.invoice_terms
        if not self.env.context.get('not_self_saleperson') or not self.team_id:
            default_team = self.env.context.get('default_team_id', False) or self.partner_id.team_id.id
            values['team_id'] = self.env['crm.team'].with_context(
                default_team_id=default_team
            )._get_default_team_id(domain=['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)], user_id=user_id)
        self.update(values)
