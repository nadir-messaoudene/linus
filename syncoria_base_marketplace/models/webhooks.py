# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
import json
from odoo import models, fields, api, exceptions, _
from ast import literal_eval

logger = logging.getLogger(__name__)


class MarketplaceWebhooks(models.Model):
    _name = 'marketplace.webhooks'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Marketplace Webhooks'
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(string='Order Reference', required=True, copy=False,
                       readonly=True, index=True, default=lambda self: _('New'))
    company_id = fields.Many2one(
        'res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    marketplace_instance_id = fields.Many2one(
        string='Select Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    marketplace_instance_type = fields.Selection(
        related='marketplace_instance_id.marketplace_instance_type',
        readonly=True,
        store=True
    )
    state = fields.Selection(
        string='state',
        selection=[('draft', 'Draft'), ('connected', 'Connected')],
        default='draft',
    )

    # @api.model
    # def create(self, vals):
    #     if 'company_id' in vals:
    #         self = self.with_company(vals['company_id'])
    #     if vals.get('name', _('New')) == _('New'):
    #         seq_date = None
    #         if 'create_date' in vals:
    #             seq_date = fields.Datetime.context_timestamp(
    #                 self, fields.Datetime.to_datetime(vals['create_date']))
    #         vals['name'] = self.env['ir.sequence'].next_by_code(
    #             'marketplace.webhooks', sequence_date=seq_date) or _('New')
