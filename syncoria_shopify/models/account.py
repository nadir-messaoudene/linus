# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api

class AccountInvoice(models.Model):
    _inherit = 'account.move'

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')]
    )
    shopify_id = fields.Integer(string="shopify Id")
    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist', string='Pricelist',
        readonly=True)


class AccountTax(models.Model):
    _inherit = 'account.tax'

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')],
    )
    shopify_id = fields.Integer(string="shopify Id")
    shopify = fields.Boolean(
        string='Shopify',
    )
    
    @api.onchange('shopify')
    def _onchange_shopify(self):
        self.write({'marketplace_type':'shopify'})
    
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')],
    )
    shopify_id = fields.Char(string="shopify Id")
    #Shopify Payment Info
    shopify_credit_card_bin = fields.Char(
        string='Credit Card BIN',
    )
    shopify_avs_result_code = fields.Char(
        string='Credit Card AVS',
    )
    shopify_cvv_result_code = fields.Char(
        string='Credit Card CVV',
    ) 
    shopify_credit_card_number = fields.Char(
        string='Credit Card Number',
    ) 
    shopify_credit_card_company = fields.Char(
        string='Credit Card Company',
    )
    shopify_payment_gateway_names = fields.Char(
        string='Payment Gateway Names',
    )



