from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
import json
from requests.auth import HTTPBasicAuth

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = "res.partner"

    resolvepay_customer_id = fields.Char(string='ResolvePay Customer Id')
    available_credit = fields.Integer(string='Available Credit', tracking=True)
    advance_rate = fields.Float(string='Advance Rate (%)', tracking=True)
    terms = fields.Char(string='Terms', tracking=True)
    net_terms_status = fields.Char(string='Net Term Status', tracking=True)
    credit_status = fields.Char(string='Credit Check Status', tracking=True)

    def create_customer_resolvepay(self):
        print('create_customer_resolvepay')
        for partner in self:
            if partner.type == 'contact':
                if not partner.street:
                    raise ValidationError('Address is required to export to ResolvePay')
                if not partner.city:
                    raise ValidationError('City is required to export to ResolvePay')
                if not partner.state_id:
                    raise ValidationError('State is required to export to ResolvePay')
                if not partner.zip:
                    raise ValidationError('Zip is required to export to ResolvePay')
                if not partner.country_id:
                    raise ValidationError('Country is required to export to ResolvePay')
                if not partner.email:
                    raise ValidationError('Email is required to export to ResolvePay')
                if not partner.phone and not partner.mobile:
                    raise ValidationError('Phone is required to export to ResolvePay')
                resolvepay_instance = self.env['resolvepay.instance'].search([('name', '=', 'ResolvePay')])
                net_term = resolvepay_instance.get_net_term(self.property_supplier_payment_term_id.name)
                partner_data = dict(
                    business_address=partner.street,
                    business_city=partner.city,
                    business_state=partner.state_id.code,
                    business_zip=partner.zip,
                    business_country=partner.country_id.code,
                    business_ap_email=partner.email,
                    business_ap_phone=partner.phone if partner.phone else partner.mobile,
                    business_name=partner.name,
                    email=partner.email,
                    default_terms=net_term,
                )
                if len(resolvepay_instance):
                    url = resolvepay_instance.instance_baseurl + 'customers'
                    res = resolvepay_instance.post_data(url=url, data=json.dumps(partner_data))
                    if res.get('data'):
                        data = res.get('data')
                        self.message_post(body="Export to ResolvePay successfully. ResolvePay Customer ID: {}".format(data.get('id')))
                        self.resolvepay_customer_id = data.get('id')
                        self.available_credit = data.get('amount_available')
                        self.advance_rate = data.get('advance_rate') * 100 if data.get('advance_rate') else data.get('advance_rate')
                        self.terms = data.get('default_terms').capitalize() if data.get('default_terms') else data.get('default_terms')
                        self.net_terms_status = data.get('net_terms_status').capitalize() if data.get('net_terms_status') else data.get('net_terms_status')
                        self.credit_status = data.get('credit_status').capitalize() if data.get('credit_status') else data.get('credit_status')
                else:
                    raise UserError('There is no ResolvePay instance')
