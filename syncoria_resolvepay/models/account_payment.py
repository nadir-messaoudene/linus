from odoo import models, fields, api, _

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    resolvepay_payment_date = fields.Char("ResolvePay payment datetime")

    def _create_payment_vals_from_wizard(self):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_wizard()
        payment_vals['resolvepay_payment_date'] = self.resolvepay_payment_date
        return payment_vals

class AccountPayment(models.Model):
    _inherit = "account.payment"

    resolvepay_payment_date = fields.Char("ResolvePay payment datetime")