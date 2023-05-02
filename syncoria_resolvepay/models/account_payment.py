from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    resolvepay_payment_date = fields.Char("ResolvePay payment datetime")

    # def _create_payment_vals_from_wizard(self):
    #     # OVERRIDE
    #     payment_vals = super()._create_payment_vals_from_wizard()
    #     payment_vals['resolvepay_payment_date'] = self.resolvepay_payment_date
    #     return payment_vals


class AccountPayment(models.Model):
    _inherit = "account.payment"

    resolvepay_payment_date = fields.Char("Resolve Pay payment datetime")
    rp_payout_transaction_id = fields.Char("Resolve Pay Payout Transaction Id")
    rp_payout_id = fields.Char("Resolve Pay Payout Id")
    rp_payout_transaction_type = fields.Selection(selection=[('advance', 'advance'),
                                                             ('payment', 'payment'),
                                                             ('refund', 'refund'),
                                                             ('monthly_fee', 'monthly_fee'), ('annual_fee', 'annual_fee'),
                                                             ('non_advanced_invoice_fee', 'non_advanced_invoice_fee'),
                                                             ('merchant_payment', 'merchant_payment'),
                                                             ('mdr_extension', 'mdr_extension'),
                                                             ('credit_note', 'credit_note')], string='Resolve Pay Transaction Type')
    rp_payout_transaction_amount_gross = fields.Float('amount_gross')
    rp_payout_transaction_amount_fee = fields.Float('amount_fee')
    rp_payout_transaction_amount_net = fields.Float('amount_net')
