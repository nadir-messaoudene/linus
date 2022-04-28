from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
import json

class Invoice(models.Model):
    _inherit = 'account.move'

    resolvepay_invoice_id = fields.Char(string='ResolvePay Invoice Id')

    def create_invoice_resolvepay(self):
        print('create_invoice_resolvepay')
        resolvepay_instance = self.env['resolvepay.instance'].search([('name', '=', 'ResolvePay')])
        if len(resolvepay_instance):
            url = resolvepay_instance.instance_baseurl + 'invoices'
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            invoice_url = base_url + '/my/invoices/' + str(self.id)
            print(invoice_url)
            if not self.partner_id.resolvepay_customer_id:
                raise ValidationError('This customer does not exist in ResolvePay')
            invoice_data = dict(
                amount=self.amount_total,
                customer_id=self.partner_id.resolvepay_customer_id,
                number=self.name,
                order_number=self.invoice_origin,
                merchant_invoice_url=invoice_url
            )
            res = resolvepay_instance.post_data(url=url, data=json.dumps(invoice_data))
            if res.get('data'):
                data = res.get('data')
                self.message_post(
                    body="Export to ResolvePay successfully. ResolvePay Invoice ID: {}".format(data.get('id')))
                self.resolvepay_invoice_id = data.get('id')
        else:
            raise UserError('There is no ResolvePay instance')