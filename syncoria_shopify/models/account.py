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

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')]
    )

    
    # def write(self, values):
    #     print("AccountInvoice===>>>write===>>>" + str(values))
    #     result = super(AccountInvoice, self).write(values)
    #     return result
    
    # @api.model
    # def create(self, values):
    #     print("AccountInvoice===>>>create===>>>" + str(values))
    #     result = super(AccountInvoice, self).create(values)
    #     return result
    
    # @api.onchange('partner_id', 'company_id')
    # def _onchange_partner_id_account_invoice_pricelist(self):
    #     result = super(AccountInvoice, self)._onchange_partner_id()
    #     if self.partner_id and self.type in ('out_invoice', 'out_refund') \
    #             and self.partner_id.property_product_pricelist:
    #         self.pricelist_id = self.partner_id.property_product_pricelist
    #     return result

    # @api.model
    # def _prepare_refund(self, invoice, date_invoice=None, date=None,
    #                     description=None, journal_id=None):
    #     values = super(AccountInvoice, self)._prepare_refund(
    #         invoice, date_invoice=date_invoice, date=date,
    #         description=description, journal_id=journal_id)
    #     if invoice.pricelist_id:
    #         values.update({
    #             'pricelist_id': invoice.pricelist_id.id,
    #         })
    #     return values


# class AccountInvoiceLine(models.Model):
#     _inherit = 'account.move.line'

#     @api.model
#     def create(self, values):
#         print("AccountInvoiceLine===>>>create===>>>" + str(values))
#         result = super(AccountInvoiceLine, self).create(values)
#         return result
    
#     @api.onchange('product_id', 'quantity', 'uom_id')
#     def _onchange_product_id_account_invoice_pricelist(self):
#         if not self.invoice_id.pricelist_id or not self.invoice_id.partner_id:
#             return
#         product = self.product_id.with_context(
#             lang=self.invoice_id.partner_id.lang,
#             partner=self.invoice_id.partner_id.id,
#             quantity=self.quantity,
#             date_order=self.invoice_id.date_invoice,
#             pricelist=self.invoice_id.pricelist_id.id,
#             uom=self.uom_id.id,
#             fiscal_position=(
#                 self.invoice_id.partner_id.property_account_position_id.id)
#         )
#         self.price_unit = self.env['account.tax']._fix_tax_included_price(
#             product.price, product.taxes_id, self.invoice_line_tax_ids)

#     def update_from_pricelist(self):

#         for line in self.filtered(lambda r: r.invoice_id.state == 'draft'):
#             line._onchange_product_id_account_invoice_pricelist()


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


    # @api.model
    # def create(self, values):
    #     print("AccountPayment--->>>values===>>>")
    #     print(values)
    #     result = super(AccountPayment, self).create(values)
    #     return result

    # def write(self, values):
    #     print("AccountPayment--->>>write--->>>values===>>>")
    #     print(values)
    #     result = super(AccountPayment, self).write(values)
    #     return result

    
    # class SaleAdvance(models.TransientModel):
    #     _inherit = 'sale.advance.payment.inv'
        
    #     @api.model
    #     def create(self, values):
    #         result = super(SaleAdvance, self).create(values)
    #         return result
    
    #     def write(self, values):
    #         result = super(SaleAdvance, self).create(values)
    #         return result
    
class AccPayRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    
    @api.model
    def create(self, values):
        print("AccPayRegister--->>>create--->>>values===>>>", values)
        result = super(AccPayRegister, self).create(values)
        return result

    def write(self, values):
        print("AccPayRegister--->>>write--->>>values===>>>", values)
        result = super(AccPayRegister, self).create(values)
        return result

