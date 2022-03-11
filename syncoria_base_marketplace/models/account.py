# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    marketplace_type = fields.Selection([], string="Marketplace Type")

class AccountMove(models.Model):
    _inherit = 'account.move'

    marketplace_type = fields.Selection([], string="Marketplace Type")

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    marketplace_type = fields.Selection([], string="Marketplace Type")
