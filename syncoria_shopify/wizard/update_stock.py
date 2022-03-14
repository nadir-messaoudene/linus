# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
from odoo import models, fields, exceptions, _
from odoo.http import request

from odoo.exceptions import UserError, ValidationError



_logger = logging.getLogger(__name__)

class ProductsFetchWizard(models.Model):
    _inherit = 'update.stock.wizard'

    fetch_type = fields.Selection([
        ('to_odoo', 'Import stock status'),
        ('from_odoo', 'Export stock status')
    ], string="Operation Type")

    def shopify_update_stock_item(self,kwargs):
        print("******shopify_update_stock_item")
        warehouse_location = self.shopify_warehouse
        marketplace_instance_id = kwargs.get('marketplace_instance_id')
        Connector = self.env['marketplace.connector']
        UpdateQtyWiz = self.env['stock.change.product.qty']
        default_location = None
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)],
                                                       limit=1)
        if warehouse:
            default_location = warehouse.lot_stock_id
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')
        api_version = marketplace_instance_id.marketplace_api_version

        cr = self._cr
        if self.fetch_type == 'to_odoo':
            url = "/admin/api/{api_version}/variants/{product_id}.json"
            url = marketplace_instance_id.marketplace_host +  url
            
            headers = {'X-Shopify-Access-Token':marketplace_instance_id.marketplace_api_password}
            type_req = 'GET'
            
            products = self._shopify_get_product_list(active_ids)

            for item in products:
                # location_id = item.location_id
                # if not location_id and default_location:
                #     location_id = default_location
                # elif not location_id:
                #     continue
                if item.default_code:
                    product_url = url.replace("{api_version}", api_version)
                    product_url = product_url.replace("{product_id}", item.shopify_id)

                    _logger.info("product_url-->", product_url)
                    stock_item = Connector.shopify_api_call(
                            headers=headers,
                            url=product_url,
                            type=type_req,
                            marketplace_instance_id=marketplace_instance_id
                    )

                    if not stock_item.get('products'):
                        stock_item["products"] = [stock_item]

                    try:
                        if stock_item.get('products'):
                            variants = stock_item.get('variants') or stock_item.get('variant')
                            variants = [variants] if type(variants) == dict else variants

                            _logger.info("variants ===>>>%s",variants)
             
                            for variant in variants:
                                if str(variant['id']) == item.shopify_id:
                                    product_stock = variant['inventory_quantity']
                                    _logger.info("product_stock ===>>>%s",product_stock)
                                    # updating qty on hand
                                    inventory_wizard = UpdateQtyWiz.create({
                                        'product_id': item.id,
                                        'product_tmpl_id': item.product_tmpl_id.id,
                                        'new_quantity': product_stock,
                                    })
                                    inventory_wizard.change_product_qty()
                                    # updating unit price if changed
                                    # if variant['price'] != item.list_price:
                                    #     cr.execute("update product_template set list_price=%s "
                                    #             "where id=%s",
                                    #             (variant['price'], item.product_tmpl_id.id))
                                    _logger.info("Successfully Updated %s", item.default_code)
                    except Exception as e:
                        _logger.warning("Exception-%s",e.args)
            return {
                'type': 'ir.actions.client',
                'tag': 'reload'
            }
        elif self.fetch_type == 'from_odoo':
            """TO DO: 'from_odoo'"""
            products = self._shopify_get_product_list(active_ids)
            headers = {
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                'Content-Type' : 'application/json'
            }
            type_req = 'POST'
            for product in products:
                product_template = product.product_tmpl_id
                try:
                    if product.type == 'product' and product.default_code and product_template.attribute_line_ids:

                            variant = {"id":product.shopify_id}
                            type_req = 'PUT'
                            host = marketplace_instance_id
                            if marketplace_instance_id.marketplace_host:
                                if '/' in marketplace_instance_id.marketplace_host[-1]:
                                    host = marketplace_instance_id.marketplace_host[0:-1]

                            if marketplace_instance_id.set_price:
                                price = product.list_price
                                if product.shopify_currency_id:
                                    price = product.shopify_price
                                variant.update({"price" : product.list_price})
                                # variant.update({"inventory_quantity" : int(product.qty_available)})
                            # if marketplace_instance_id.publish_in_website:
                            #     variant.update({"inventory_quantity" : int(product.qty_available)})
                            # if marketplace_instance_id.set_image:
                            #     variant.update({"inventory_quantity" : int(product.qty_available)})

                            if marketplace_instance_id.set_stock and product.qty_available and self.shopify_warehouse:
                                update_qty = self._shopify_update_qty(warehouse=warehouse_location.partner_id.shopify_warehouse_id,inventory_item_id=product.shopify_inventory_id,quantity=int(product.qty_available),marketplace_instance_id=marketplace_instance_id,host=host)

                            data = {'variant': variant}
                            product_url = host.marketplace_host + "/admin/api/%s/variants/%s.json" %(api_version, product.shopify_id)
                            stock_item = Connector.shopify_api_call(
                                headers=headers,
                                url=product_url,
                                type=type_req,
                                data=data
                            )
                            _logger.info("stock_item: %s" % (stock_item))
                            if 'call_button' in str(request.httprequest) and stock_item.get('errors'):
                                errors = stock_item.get('errors', {}).get('error')
                                raise UserError(_("Request Error: %s" % (errors)))

                    if not product_template.attribute_line_ids:
                        if marketplace_instance_id.set_stock and product.qty_available and self.shopify_warehouse:
                            host = marketplace_instance_id
                            if marketplace_instance_id.marketplace_host:
                                if '/' in marketplace_instance_id.marketplace_host[-1]:
                                    host = marketplace_instance_id.marketplace_host[0:-1]

                            update_qty = self._shopify_update_qty(
                                warehouse=warehouse_location.partner_id.shopify_warehouse_id,
                                inventory_item_id=product.shopify_inventory_id, quantity=int(product.qty_available),
                                marketplace_instance_id=marketplace_instance_id, host=host)
                except Exception as e:
                    _logger.warning("Error in Request: %s" % (e.args))


            return {
                'type': 'ir.actions.client',
                'tag': 'reload'
            }

        # if 'call_button' in str(request.httprequest):
        #     return {
        #         'name': ('Shopify Orders'),
        #         'type': 'ir.actions.act_window',
        #         'view_type': 'form',
        #         'view_mode': 'tree,form',
        #         'res_model': 'sale.order',
        #         'view_id': False,
        #         'domain': [('marketplace_type', '=', 'shopify')],
        #         'target': 'current',
        #     }
        # else:
        #     return {
        #         'type': 'ir.actions.client',
        #         'tag': 'reload'
        #     }

        # return



    def _shopify_update_qty(self,**kwargs):
        Connector = self.env['marketplace.connector']

        data = {"location_id": kwargs['warehouse'],"inventory_item_id":kwargs['inventory_item_id'],"available": kwargs['quantity']
        }

        headers = {
            'X-Shopify-Access-Token': kwargs["marketplace_instance_id"].marketplace_api_password,
            'Content-Type': 'application/json'
        }

        type_req = 'POST'

        version = kwargs["marketplace_instance_id"].marketplace_api_version
        # product_url = host.marketplace_host + "/admin/api/%s/variants/%s.json" %(version, product.shopify_id)
        product_url = kwargs["host"].marketplace_host + "/admin/api/%s/inventory_levels/set.json" % (version)
        stock_item = Connector.shopify_api_call(
            headers=headers,
            url=product_url,
            type=type_req,
            data=data
        )
        _logger.info("stock_item: %s" % (stock_item))
        if 'call_button' in str(request.httprequest) and stock_item.get('errors'):
            errors = stock_item.get('errors', {}).get('error')
            raise errors


    def _shopify_get_product_list(self, active_ids):
        if self._context.get('active_model') == 'product.product':
            products = self.env['product.product'].search([
                ('marketplace_type', '=', 'shopify'),
                ('id', 'in', active_ids)
            ])
            # product_templ_id =
        if self._context.get('active_model') == 'product.template':
            # Cannot find products
            products = self.env['product.product'].search([
                ('marketplace_type', '=', 'shopify'),
                ('product_tmpl_id', 'in', active_ids)
            ])
        return products