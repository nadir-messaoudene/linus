# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import requests
import logging
import base64
import re
from odoo import models, fields, exceptions, _
from odoo.http import request
from pprint import pprint

from odoo import api

_logger = logging.getLogger(__name__)


class WarehouseFetchWizard(models.TransientModel):
    _name = 'shopify.warehouse.fetch.wizard'
    _description = 'Shopify Warehouse Wizard'

    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )

    def _get_instance_id(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        try:
            marketplace_instance_id = ICPSudo.get_param(
                'syncoria_base_marketplace.marketplace_instance_id')
            marketplace_instance_id = [int(s) for s in re.findall(
                r'\b\d+\b', marketplace_instance_id)]
        except:
            marketplace_instance_id = False

        if marketplace_instance_id:
            marketplace_instance_id = self.env['marketplace.instance'].sudo().search(
                [('id', '=', marketplace_instance_id[0])])
        return marketplace_instance_id


    def fetch_warehouse_to_odoo(self):
        # Add code here
        marketplace_instance_id = self._get_instance_id()
        if marketplace_instance_id:
            version = marketplace_instance_id.marketplace_api_version
            url = marketplace_instance_id.marketplace_host + \
                  '/admin/api/%s/locations.json' % version

            # if kwargs.get('fetch_o_product'):
            #     # /admin/api/2021-04/products/{product_id}.json
            #     url = marketplace_instance_id.marketplace_host + \
            #           '/admin/api/%s/products/%s.json' % (
            #               version, kwargs.get('product_id'))

            _logger.info("Product URL-->" + str(url))

            headers = {
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password }
            type_req = 'GET'

            inventory_locations,next_link = self.env[
                'marketplace.connector'].shopify_api_call(
                headers=headers,
                url=url,
                type=type_req,
                marketplace_instance_id=marketplace_instance_id
            )
            print(inventory_locations)
            shopify_warehouse = self.env['shopify.warehouse']
            for location in inventory_locations["locations"]:

                vals = {
                    "shopify_invent_id" : location.get("id"),
                    "shopify_loc_name" : location.get("name"),
                    "shopify_loc_add_one" : location.get("address1"),
                    "shopify_loc_add_two" : location.get("address2"),
                    "shopify_loc_city" : location.get("city"),
                    "shopify_loc_zip" : location.get("zip"),
                    "shopify_loc_province" : location.get("province"),
                    "shopify_loc_country" : location.get("country"),
                    "shopify_loc_phone" : location.get("phone"),
                    "shopify_loc_created_at" : location.get("created_at"),
                    "shopify_loc_updated_at" : location.get("updated_at"),
                    "shopify_loc_country_code" : location.get("country_code"),
                    "shopify_loc_country_name" : location.get("country_name"),
                    "shopify_loc_country_province_code" : location.get("province_code"),
                    "shopify_loc_legacy" : location.get("legacy"),
                    "shopify_loc_active" : location.get("active"),
                    "shopify_loc_localized_country_name" : location.get("localized_country_name"),
                    "shopify_loc_localized_province_name" : location.get("localized_province_name"),
                    "shopify_instance_id" : marketplace_instance_id.id,
                }

                exists_warehouse = shopify_warehouse.search([("shopify_invent_id", "=", location.get("id"))])
                if not exists_warehouse:
                    shopify_warehouse.create(vals)
                else:
                    exists_warehouse.update(vals)







        else:
            exceptions.UserError("Please Set Shopify in Marketplace selection.")


