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

    def fetch_shopify_payments(self):
        SaleOrder = self.env['sale.order'].sudo()
        sp_order_obj = SaleOrder.search([('name', '=', self.ref)], limit=1)
        sp_order_obj.fetch_shopify_payments()
    def fetch_shopify_refunds(self):
        SaleOrder = self.env['sale.order'].sudo()
        sp_order_obj = SaleOrder.search([('name', '=', self.ref)], limit=1)
        sp_order_obj.fetch_shopify_refunds()
    def process_shopify_invoice(self):
        SaleOrder = self.env['sale.order'].sudo()
        sp_order_obj = SaleOrder.search([('name', '=', self.ref)], limit=1)
        sp_order_obj.process_shopify_invoice()
    def shopify_invoice_register_payments(self):
        SaleOrder = self.env['sale.order'].sudo()
        sp_order_obj = SaleOrder.search([('name', '=', self.ref)], limit=1)
        sp_order_obj.shopify_invoice_register_payments()
    def process_shopify_credit_note(self):
        SaleOrder = self.env['sale.order'].sudo()
        sp_order_obj = SaleOrder.search([('name', '=', self.ref)], limit=1)
        sp_order_obj.process_shopify_credit_note()
    def shopify_credit_note_register_payments(self):
        SaleOrder = self.env['sale.order'].sudo()
        sp_order_obj = SaleOrder.search([('name', '=', self.ref)], limit=1)
        sp_order_obj.shopify_credit_note_register_payments()
    
    


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



