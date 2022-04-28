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
                    # default_terms='/',
                )
                resolvepay_instance = self.env['resolvepay.instance'].search([('name', '=', 'ResolvePay')])
                if len(resolvepay_instance):
                    url = resolvepay_instance.instance_baseurl + 'customers'
                    res = resolvepay_instance.post_data(url=url, data=json.dumps(partner_data))
                    if res.get('data'):
                        data = res.get('data')
                        self.message_post(body="Export to ResolvePay successfully. ResolvePay Customer ID: {}".format(data.get('id')))
                        self.resolvepay_customer_id = data.get('id')
