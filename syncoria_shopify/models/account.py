# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


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
    # def shopify_invoice_register_payments(self):
    #     SaleOrder = self.env['sale.order'].sudo()
    #     sp_order_obj = SaleOrder.search([('name', '=', self.ref)], limit=1)
    #     sp_order_obj.shopify_invoice_register_payments()
    def shopify_invoice_register_payments(self):
        for rec in self:
            sale_order_id = rec.invoice_line_ids.mapped('sale_line_ids').order_id
            success_tran_ids = sale_order_id.shopify_transaction_ids.filtered(lambda l: l.shopify_status == 'success')
            try:
                if len(sale_order_id) == 1:
                    for tran_id in success_tran_ids:
                        payment_id = self.env['account.payment'].search([('shopify_id', '=', tran_id.shopify_id)])
                        if not payment_id:
                            shopify_instance_id = tran_id.shopify_instance_id or sale_order_id.shopify_instance_id
                            if float(
                                    tran_id.shopify_amount) > 0 and shopify_instance_id and rec.payment_state != 'in_payment':
                                shopify_amount = float(tran_id.shopify_amount)
                                if tran_id.shopify_currency and tran_id.shopify_amount:
                                    if tran_id.shopify_currency != tran_id.shopify_instance_id.pricelist_id.currency_id.name:
                                        shopify_amount = float(tran_id.shopify_amount) * float(
                                            tran_id.shopify_exchange_rate)
                                _logger.info("shopify_amount==>>>{}".format(shopify_amount))
                                journal_id = self.env['account.journal'].search([('gateway', '=', tran_id.shopify_gateway)])
                                if not journal_id:
                                    journal_id = shopify_instance_id.marketplace_payment_journal_id
                                wizard_vals = {
                                    'journal_id': journal_id.id,
                                    'amount': shopify_amount,
                                    'payment_date': fields.Datetime.now(),
                                }

                                payment_method_line_id = journal_id.inbound_payment_method_line_ids.filtered(
                                    lambda
                                        l: l.payment_method_id.id == shopify_instance_id.marketplace_inbound_method_id.id)
                                if payment_method_line_id:
                                    wizard_vals['payment_method_line_id'] = payment_method_line_id.id

                                wizard_vals['payment_date'] = tran_id.shopify_processed_at.split('T')[
                                    0] if tran_id.shopify_processed_at else fields.Datetime.now()
                                pmt_wizard = self.env['account.payment.register'].with_context(
                                    active_model='account.move',
                                    active_ids=rec.ids).create(wizard_vals)

                                payment = pmt_wizard._create_payments()
                                payment.shopify_id = tran_id.shopify_id
                                print("===============>", payment)
                                if rec.payment_state in ['paid', 'in_payment']:
                                    sale_order_id.write({"shopify_is_invoice": True})

            except Exception as e:
                _logger.warning("Exception-{}-{}".format(rec.name, e.args))

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


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    gateway = fields.Char('Gateway')



