# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import json
import logging
import datetime
from odoo import fields, models, exceptions, _
from odoo.http import request
import re
import pprint

from odoo.exceptions import UserError, ValidationError



_logger = logging.getLogger(__name__)


def get_instance_id(model):
    ICPSudo = model.env['ir.config_parameter'].sudo()
    try:
        marketplace_instance_id = ICPSudo.get_param(
            'syncoria_base_marketplace.marketplace_instance_id')
        marketplace_instance_id = [int(s) for s in re.findall(
            r'\b\d+\b', marketplace_instance_id)]
    except:
        marketplace_instance_id = False

    if marketplace_instance_id:
        marketplace_instance_id = model.env['marketplace.instance'].sudo().search(
            [('id', '=', marketplace_instance_id[0])])
    return marketplace_instance_id

class ProductsFetchWizard(models.Model):
    _inherit = 'update.stock.wizard'

    fetch_type = fields.Selection([
        ('to_odoo', 'Import stock status'),
        ('from_odoo', 'Export stock status')
    ], string="Operation Type")




    def action_update_stock_item(self):
        print("""action_update_stock_item===>>>>""")
        Connector = self.env['marketplace.connector']
        marketplace_instance_id = get_instance_id(self)
        warehouse_location = self.shopify_warehouse
        self.fetch_type == 'from_odoo'
        kwargs = {}
        kwargs['marketplace_instance_id'] = marketplace_instance_id.id
        domain = [('shopify_instance_id', '=', marketplace_instance_id.id)]
        domain += [('shopify_id', 'not in', (False, ''))]
        product_tmpl_ids = self.env['product.template'].sudo().search(domain)
        active_ids = product_tmpl_ids.ids
        print("""active_ids===>>>>""", active_ids)

        domain = [('shopify_instance_id', '=', marketplace_instance_id.id)]
        domain += [('shopify_id', 'not in', (False, ''))]
        product_ids = self.env['product.product'].sudo().search(domain)
        active_ids = product_ids.ids
        print("""active_ids===>>>>""", active_ids)
        api_version = marketplace_instance_id.marketplace_api_version


        headers = {
            'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
            'Content-Type' : 'application/json'
        }
        type_req = 'POST'
        for product in product_ids:
            product_template = product.product_tmpl_id
            try:
                if product.type == 'product' and product.shopify_id and product_template.attribute_line_ids:
                    variant = {"id":product.shopify_id}
                    type_req = 'PUT'
                    host = marketplace_instance_id.marketplace_host
                    if marketplace_instance_id.marketplace_host:
                        if '/' in marketplace_instance_id.marketplace_host[-1]:
                            host = marketplace_instance_id.marketplace_host[0:-1]
                    print("HOST===>>>",host)

                    if marketplace_instance_id.set_price:
                        price = product.list_price
                        if product.shopify_currency_id:
                            price = product.shopify_price
                        variant.update({"price" : product.list_price})

                    if self.shopify_warehouse:
                        update_qty = self._shopify_update_qty(
                            warehouse=self.shopify_warehouse.shopify_warehouse_id,
                            inventory_item_id=product.shopify_inventory_id, quantity=int(product.with_context({"warehouse":self.shopify_warehouse.id}).qty_available),
                            marketplace_instance_id=marketplace_instance_id, host=host)
                    else:
                        quants_ids = product.stock_quant_ids.search([("location_id.usage","=","internal"),("product_id","=",product.id)])
                        for quants in quants_ids:
                            if marketplace_instance_id.set_stock and product.qty_available and quants.location_id.warehouse_id.shopify_warehouse_active:
                                update_qty = self._shopify_update_qty(
                                    warehouse=quants.location_id.warehouse_id.shopify_warehouse_id,
                                    inventory_item_id=product.shopify_inventory_id,
                                    quantity=int(quants.quantity),
                                    marketplace_instance_id=marketplace_instance_id,
                                    host=host)

                    data = {'variant': variant}
                    product_url = host + "/admin/api/%s/variants/%s.json" %(api_version, product.shopify_id)
                    stock_item,next_link = Connector.shopify_api_call(
                        headers=headers,
                        url=product_url,
                        type=type_req,
                        data=data
                    )
                    _logger.info("stock_item: %s" % (stock_item))
                    if 'call_button' in str(request.httprequest) and stock_item.get('errors'):
                        errors = stock_item.get('errors', {}).get('error')
                        _logger.warning(_("Request Error: %s" % (errors)))

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





    def shopify_update_stock_item(self,kwargs):
        _logger.info("******shopify_update_stock_item")
        warehouse_location = self.shopify_warehouse
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


        cr = self._cr
        if self.fetch_type == 'to_odoo':

            type_req = 'GET'
            
            products = self._shopify_get_product_list(active_ids)

            for item in products:
                try:
                    # ==================== Marketplace Credentials =================
                    marketplace_instance_id = item.shopify_instance_id
                    api_version = marketplace_instance_id.marketplace_api_version
                    url = f"/admin/api/{api_version}/inventory_levels.json"
                    url = marketplace_instance_id.marketplace_host +  url

                    headers = {'X-Shopify-Access-Token':marketplace_instance_id.marketplace_api_password}
                    # ===================================================================

                    params = {"inventory_item_ids":item.shopify_inventory_id}
                    _logger.info("product_url-->", url)
                    stock_item,next_link = Connector.shopify_api_call(
                            headers=headers,
                            url=url,
                            type=type_req,
                            marketplace_instance_id=marketplace_instance_id,
                            params=params
                    )

                    if stock_item.get('inventory_levels'):
                        inventory_stocks = stock_item.get('inventory_levels')
                        for stocks_info in inventory_stocks:
                            self.change_product_qty(stocks_info,item)



                except Exception as e:
                    _logger.warning("Exception-%s",e.args)

            return {
                'type': 'ir.actions.client',
                'tag': 'reload'
            }
        elif self.fetch_type == 'from_odoo':
            """TO DO: 'from_odoo'"""
            products = self._shopify_get_product_list(active_ids)

            for product in products:
                try:
                    marketplace_instance_id = product.shopify_instance_id
                    api_version = marketplace_instance_id.marketplace_api_version
                    headers = {
                        'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                        'Content-Type': 'application/json'
                    }

                    product_template = product.product_tmpl_id

                    if product.type == 'product' and product.shopify_id and product_template.attribute_line_ids:
                        variant = {"id":product.shopify_id}
                        type_req = 'PUT'
                        host = marketplace_instance_id.marketplace_host
                        if marketplace_instance_id.marketplace_host:
                            if '/' in marketplace_instance_id.marketplace_host[-1]:
                                host = marketplace_instance_id.marketplace_host[0:-1]
                        print("HOST===>>>",host)

                        if marketplace_instance_id.set_price:
                            price = product.list_price
                            if product.shopify_currency_id:
                                price = product.shopify_price
                            variant.update({"price" : product.list_price})

                        if self.shopify_warehouse:
                            update_qty = self._shopify_update_qty(
                                warehouse=self.shopify_warehouse.shopify_warehouse_id,
                                inventory_item_id=product.shopify_inventory_id, quantity=int(product.with_context({"warehouse":self.shopify_warehouse.id}).qty_available),
                                marketplace_instance_id=marketplace_instance_id, host=host)
                        else:
                            quants_ids = product.stock_quant_ids.search([("location_id.usage","=","internal"),("product_id","=",product.id)])
                            for quants in quants_ids:
                                if marketplace_instance_id.set_stock and product.qty_available and quants.location_id.warehouse_id.shopify_warehouse_active:
                                    update_qty = self._shopify_update_qty(
                                        warehouse=quants.location_id.warehouse_id.shopify_warehouse_id,
                                        inventory_item_id=product.shopify_inventory_id,
                                        quantity=int(quants.quantity),
                                        marketplace_instance_id=marketplace_instance_id,
                                        host=host)

                        data = {'variant': variant}
                        product_url = host + "/admin/api/%s/variants/%s.json" %(api_version, product.shopify_id)
                        stock_item,next_link = Connector.shopify_api_call(
                            headers=headers,
                            url=product_url,
                            type=type_req,
                            data=data
                        )
                        _logger.info("stock_item: %s" % (stock_item))
                        if 'call_button' in str(request.httprequest) and stock_item.get('errors'):
                            errors = stock_item.get('errors', {}).get('error')
                            _logger.warning(_("Request Error: %s" % (errors)))

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

    def change_product_qty(self,stock_info,product_info):
        warehouse = self.env['stock.warehouse'].search([("shopify_warehouse_id","=",stock_info.get("location_id")),("shopify_warehouse_active","=",True)],limit=1)
        # Before creating a new quant, the quand `create` method will check if
        # it exists already. If it does, it'll edit its `inventory_quantity`
        # instead of create a new one.
        if warehouse:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product_info.id,
                'location_id': warehouse.lot_stock_id.id,
                'inventory_quantity': stock_info.get('available'),
            }).action_apply_inventory()

    def _shopify_update_qty(self,**kwargs):
        Connector = self.env['marketplace.connector']

        data = {
            "location_id": kwargs['warehouse'],
            "inventory_item_id":kwargs['inventory_item_id'],
            "available": kwargs['quantity']
        }

        headers = {
            'X-Shopify-Access-Token': kwargs["marketplace_instance_id"].marketplace_api_password,
            'Content-Type': 'application/json'
        }

        type_req = 'POST'

        version = kwargs["marketplace_instance_id"].marketplace_api_version
        # product_url = host.marketplace_host + "/admin/api/%s/variants/%s.json" %(version, product.shopify_id)
        if kwargs.get('host'):
            product_url = kwargs["host"] + "/admin/api/%s/inventory_levels/set.json" % (version)
        else:
            product_url = kwargs["marketplace_host"].marketplace_host + "/admin/api/%s/inventory_levels/set.json" % (version)

        stock_item,next_link = Connector.shopify_api_call(
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
                ('id', 'in', active_ids),
                ('shopify_id', 'not in', ['', False])
            ])
            # product_templ_id =
        if self._context.get('active_model') == 'product.template':
            # Cannot find products
            products = self.env['product.product'].search([
                ('marketplace_type', '=', 'shopify'),
                ('product_tmpl_id', 'in', active_ids),
                ('shopify_id','not in',['',False])
            ])
        return products