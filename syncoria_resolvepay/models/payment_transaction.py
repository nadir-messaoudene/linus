# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re
from odoo import api, fields, models, _, SUPERUSER_ID
_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _set_pending(self, state_message=None):
        """ Override of payment to send the quotations automatically. """
        for record in self:
            if record.acquirer_id.id == 18:
                for so in record.sale_order_ids.filtered(lambda so: so.state in ['draft', 'sent']):
                    payment_term_id = self.env['account.payment.term'].sudo().search([('name', '=', 'NET 30')], limit=1)
                    if payment_term_id:
                        so.payment_term_id = payment_term_id.id
        super(PaymentTransaction, self)._set_pending(state_message=state_message)
        for record in self:
            if record.acquirer_id.id == 18:
                for so in record.sale_order_ids.filtered(lambda so: so.state in ['draft', 'sent']):
                    so.tag_ids = [(3, tag.id) for tag in so.tag_ids if tag.name != 'B2B']
                    so.sudo().action_confirm()
                    invoice_id = so.sudo()._create_invoices()
                    invoice_id.sudo().action_post()
                    invoice_id.sudo().create_invoice_resolvepay()
            else:
                if record.acquirer_id.provider == 'authorize' and record.state in ['pending', 'cancel', 'error']:
                    tag_id = self.env['crm.tag'].sudo().search([('name', '=', 'PENDING')])
                    if not tag_id:
                        tag_id = self.env['crm.tag'].sudo().create({"name": 'PENDING', "color": 1})
                    if tag_id:
                        for so in record.sale_order_ids.filtered(lambda so: so.state in ['draft', 'sent']):
                            so.tag_ids = [(4, tag_id.id)]

    def _set_canceled(self, state_message=None):
        super(PaymentTransaction, self)._set_canceled(state_message=state_message)
        for tx in self:
            if tx.acquirer_id.provider == 'authorize' and tx.state in ['pending', 'cancel', 'error']:
                tag_id = self.env['crm.tag'].sudo().search([('name', '=', 'PENDING')])
                if not tag_id:
                    tag_id = self.env['crm.tag'].sudo().create({"name": 'PENDING', "color": 1})
                if tag_id:
                    for so in tx.sale_order_ids.filtered(lambda so: so.state in ['draft', 'sent']):
                        so.tag_ids = [(4, tag_id.id)]

    def _set_done(self, state_message=None):
        super(PaymentTransaction, self)._set_done(state_message=state_message)
        for tx in self:
            for so in tx.sale_order_ids:
                so.tag_ids = [(3, tag.id) for tag in so.tag_ids if tag.name != 'B2B']
