# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, exceptions, _
from odoo.http import request
import re
import logging

logger = logging.getLogger(__name__)


class CustomerFetchWizard(models.Model):
    _inherit = 'order.fetch.wizard'


    def shopify_fetch_customers_to_odoo(self, kwargs=None):
        """
            Fetch Customers
            res.partner(type): mapping
                Odoo Type       Shopify Type
                contact         default
                invoice                  
                delivery
                other
                private
            
        """
        if not kwargs:
            ICPSudo = self.env['ir.config_parameter'].sudo()
            try:
                marketplace_instance_id = ICPSudo.get_param('syncoria_base_marketplace.marketplace_instance_id')
                marketplace_instance_id = [int(s) for s in re.findall(r'\b\d+\b', marketplace_instance_id)]
                marketplace_instance_id = self.env['marketplace.instance'].sudo().search([('id','=',marketplace_instance_id[0])])
                kwargs = {'marketplace_instance_id': marketplace_instance_id } 
            except:
                marketplace_instance_id = False

        PartnerObj = self.env['res.partner']
        cr = self._cr

        if len(kwargs.get('marketplace_instance_id')) > 0:
            marketplace_instance_id = kwargs.get('marketplace_instance_id')
            version = marketplace_instance_id.marketplace_api_version or '2021-01'
            url = marketplace_instance_id.marketplace_host +  '/admin/api/%s/customers.json'%version
            headers = {'X-Shopify-Access-Token':marketplace_instance_id.marketplace_api_password}
            type_req = 'GET'
            params = {"limit":250}
            items=[]
            while True:
                customer_list,next_link = self.env['marketplace.connector'].marketplace_api_call(headers=headers, url=url, type=type_req,marketplace_instance_id=marketplace_instance_id,params=params)
                items += customer_list['customers']
                if next_link:
                    if next_link.get("next"):
                        url = next_link.get("next").get("url")

                    else:
                        break
                else:
                    break

            try:
                cr.execute("select shopify_id from res_partner "
                           "where shopify_id is not null")
                partners = cr.fetchall()
                partner_ids = [i[0] for i in partners] if partners else []

                # need to fetch the complete required fields list
                # and their values

                cr.execute("select id from ir_model "
                           "where model='res.partner'")
                partner_model = cr.fetchone()

                if not partner_model:
                    return
                cr.execute("select name from ir_model_fields "
                           "where model_id=%s and required=True ",
                           (partner_model[0], ))
                res = cr.fetchall()
                fields_list = [i[0] for i in res if res] or []
                partner_vals = PartnerObj.default_get(fields_list)

                for i in items:
                    if str(i['id']) not in partner_ids:
                        customer_id = self.shopify_find_customer_id(
                            i,
                            partner_ids,
                            partner_vals,
                            main=True
                        )

                        if customer_id:
                            PartnerObj.browse(customer_id).write({"shopify_instance_id":marketplace_instance_id.id})
                            logger.info(
                                "Customer is created with id %s", customer_id)
                        else:
                            logger.info("Unable to create Customer")
                    else:

                        partner = PartnerObj.search([("shopify_id","=",i['id'])],limit=1)
                        partner.write({"shopify_instance_id": marketplace_instance_id.id})
                        tags = i.get('tags').split(",")
                        try:
                            tag_ids = []
                            for tag in tags:
                                tag_id = self.env['res.partner.category'].search([
                                    ("name", "=", tags),
                                    ("parent_id", "=", self.env.ref("syncoria_shopify.shopify_tag").id)
                                ], limit=1)
                                if not tag_id and tag != "":
                                    tag_id = self.env['res.partner.category'].create(
                                        {"name": tag, "color": 1, "active": True,
                                         "parent_id": self.env.ref("syncoria_shopify.shopify_tag").id}
                                    )
                                    # current_order_id.write({"tag_ids":[(0,0, {"name": tag, "color": 1}))
                                if tag_id:
                                    tag_ids.append(tag_id.id)
                            partner.category_id = tag_ids
                        except Exception as e:
                            logger.warning(e)




                # self.update_sync_history({
                #     'last_product_sync' : '',
                #     'last_product_sync_id' : sp_product_list[-1].get('id') if len(sp_product_list) > 0 else '',
                #     'product_sync_no': update_products_no,
                # })
                
                if 'call_button'  in str(request.httprequest):
                    return {
                        'name': ('Shopify Customers'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'res.partner',
                        'view_id': False,
                        'domain': [('marketplace_type', '=', 'shopify')],
                        'target':'current',
                    }
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload'
                }

            except Exception as e:
                if customer_list.get('errors'):
                    e = customer_list.get('errors')
                logger.info("Exception occured: %s", e)
                raise exceptions.UserError(_("Error Occured: %s") % e)
