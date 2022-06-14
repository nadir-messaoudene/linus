# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, exceptions, _,fields
import logging
import re

logger = logging.getLogger(__name__)


class CustomerFetchWizard(models.Model):
    _name = 'customer.fetch.wizard'
    _description = 'Customer Fetch Wizard'
    _inherit = 'order.fetch.wizard'

    def fetch_customers_to_odoo(self):
        print("fetch_customers_to_odoo")
        ICPSudo = self.env['ir.config_parameter'].sudo()
        try:
            marketplace_instance_id = ICPSudo.get_param('syncoria_base_marketplace.marketplace_instance_id')
            marketplace_instance_id = [int(s) for s in re.findall(r'\b\d+\b', marketplace_instance_id)]
        except:
            marketplace_instance_id = False
            pass
        print(marketplace_instance_id)
        if marketplace_instance_id:
            if self.instance_id:
                marketplace_instance_id =self.instance_id
            else:
                marketplace_instance_id = self.env['marketplace.instance'].sudo().search([('id','=',marketplace_instance_id[0])])
            kwargs = {'marketplace_instance_id': marketplace_instance_id}
            if hasattr(self, '%s_fetch_customers_to_odoo' % marketplace_instance_id.marketplace_instance_type):
                return getattr(self, '%s_fetch_customers_to_odoo' % marketplace_instance_id.marketplace_instance_type)(kwargs)
