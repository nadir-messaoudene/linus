# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import json

from odoo import api, fields, models, SUPERUSER_ID, _, Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.osv import expression
from odoo.tools import float_is_zero, html_keep_url, is_html_empty


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    payment_acquirer_id = fields.Many2one('payment.acquirer', related='payment_method_line_id.payment_acquirer_id', string="Acquirer")

    @api.depends('payment_method_line_id')
    def _compute_suitable_payment_token_ids(self):
        print('INHERTI _compute_suitable_payment_token_ids')
        for wizard in self:
            print(wizard.payment_method_line_id)
            if wizard.can_edit_wizard and wizard.use_electronic_payment_method:
                related_partner_ids = (
                        wizard.partner_id
                        | wizard.partner_id.commercial_partner_id
                        | wizard.partner_id.commercial_partner_id.child_ids
                )._origin

                suitable_payment_token_ids = self.env['payment.token'].sudo().search([
                    ('company_id', '=', wizard.company_id.id),
                    ('acquirer_id.capture_manually', '=', False),
                    ('partner_id', 'in', related_partner_ids.ids),
                    ('acquirer_id', '=', wizard.payment_method_line_id.payment_acquirer_id.id),
                ])
                #Get all Token for All Authorize Acquirer
                if wizard.payment_method_line_id.code == 'authorize':
                    payment_acquirer_ids = self.env['payment.acquirer'].search([('provider', '=', 'authorize')])
                    suitable_payment_token_ids = self.env['payment.token'].sudo().search([
                        ('company_id', '=', wizard.company_id.id),
                        ('acquirer_id.capture_manually', '=', False),
                        ('partner_id', 'in', related_partner_ids.ids),
                        ('acquirer_id', 'in', payment_acquirer_ids.ids),
                    ])
                #End
                wizard.suitable_payment_token_ids = suitable_payment_token_ids
            else:
                wizard.suitable_payment_token_ids = [Command.clear()]