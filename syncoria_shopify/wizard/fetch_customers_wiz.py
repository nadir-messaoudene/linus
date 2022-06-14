# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, exceptions, _
from odoo.http import request
import re
import json
import logging

_logger = logging.getLogger(__name__)


class CustomerFetchWizard(models.Model):
    _inherit = 'order.fetch.wizard'

    def create_feed_customer(self, customer_data):
        feed_customer_id = False
        try:
            domain = [('shopify_id', '=', customer_data['id'])]
            feed_customer_id = self.env['shopify.feed.customers'].sudo().search(domain, limit=1)
            if not feed_customer_id:
                feed_customer_id = self.env['shopify.feed.customers'].sudo().create({
                    'name': self.env['ir.sequence'].next_by_code('shopify.feed.customers'),
                    'instance_id': self.instance_id.id,
                    'shopify_id': customer_data['id'],
                    'customer_data': json.dumps(customer_data),
                    'state': 'draft',
                    'customer_name': customer_data.get('first_name') + ' ' + customer_data.get('last_name'),
                    'email': customer_data.get('email'),
                })
                feed_customer_id._cr.commit()
                _logger.info(
                    "Shopify Feed customer Created-{}".format(feed_customer_id))
        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))
        return feed_customer_id

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
                marketplace_instance_id = self.env['marketplace.instance'].sudo().search(
                    [('id', '=', marketplace_instance_id[0])])
                kwargs = {'marketplace_instance_id': marketplace_instance_id}
            except:
                marketplace_instance_id = False

        PartnerObj = self.env['res.partner']
        cr = self._cr

        if len(kwargs.get('marketplace_instance_id')) > 0:
            marketplace_instance_id = kwargs.get('marketplace_instance_id')
            version = marketplace_instance_id.marketplace_api_version or '2021-01'
            url = marketplace_instance_id.marketplace_host + '/admin/api/%s/customers.json' % version

            tz_offset = '-00:00'
            if self.env.user and self.env.user.tz_offset:
                tz_offset = self.env.user.tz_offset

            if self.date_from and not self.date_to:
                url += '?created_at_min=%s' % self.date_from.strftime(
                    "%Y-%m-%dT00:00:00" + tz_offset)
            if not self.date_from and self.date_to:
                url += '?created_at_max=%s' % self.date_to.strftime(
                    "%Y-%m-%dT23:59:59" + tz_offset)
            if self.date_from and self.date_to:
                url += '?created_at_min=%s' % self.date_from.strftime(
                    "%Y-%m-%dT00:00:00" + tz_offset)
                url += '&created_at_max=%s' % self.date_to.strftime(
                    "%Y-%m-%dT23:59:59" + tz_offset)
            if not self.date_from and not self.date_to:
                url += '?created_at_min=%s' % fields.Datetime.now().strftime(
                    "%Y-%m-%dT00:00:00" + tz_offset)
                url += '&created_at_max=%s' % fields.Datetime.now().strftime(
                    "%Y-%m-%dT23:59:59" + tz_offset)

            _logger.info("url===>>>>{}".format(url))

            headers = {'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password}
            type_req = 'GET'
            params = {"limit": 250}
            items = []
            while True:
                customer_list, next_link = self.env['marketplace.connector'].marketplace_api_call(headers=headers,
                                                                                                  url=url,
                                                                                                  type=type_req,
                                                                                                  marketplace_instance_id=marketplace_instance_id,
                                                                                                  params=params)
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
                           (partner_model[0],))
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
                            PartnerObj.browse(customer_id).write({"shopify_instance_id": marketplace_instance_id.id})
                            _logger.info(
                                "Customer is created with id %s", customer_id)
                        else:
                            _logger.info("Unable to create Customer")
                    else:

                        partner = PartnerObj.search([("shopify_id", "=", i['id'])], limit=1)
                        partner_updates = {
                            "shopify_instance_id": marketplace_instance_id.id,
                            "name": (i.get(
                                'first_name') or "") + " " + (i.get('last_name') or ""),
                            "phone": i.get('phone') or "",
                            "email": i.get('email') or "",
                            "shopify_last_order_id": i.get('last_order_name') or "",
                            "shopify_total_spent": i.get('total_spent') or "",
                            "comment": i.get('note') or "",
                            "shopify_state": i.get('state'),
                        }
                        self._process_addresses(partner_updates,i)
                        partner.write(partner_updates)
                        tags = i.get('tags').split(",")
                        try:
                            tag_ids = []
                            for tag in tags:
                                tag_id = self.env['res.partner.category'].search([
                                    ("name", "=", tag),
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
                            if tag_ids:
                                partner.category_id = tag_ids
                            else:
                                partner.category_id.unlink()
                        except Exception as e:
                            _logger.warning(e)

                # self.update_sync_history({
                #     'last_product_sync' : '',
                #     'last_product_sync_id' : sp_product_list[-1].get('id') if len(sp_product_list) > 0 else '',
                #     'product_sync_no': update_products_no,
                # })

                if 'call_button' in str(request.httprequest):
                    return {
                        'name': ('Shopify Customers'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'res.partner',
                        'view_id': False,
                        'domain': [('marketplace_type', '=', 'shopify')],
                        'target': 'current',
                    }
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload'
                }

            except Exception as e:
                if customer_list.get('errors'):
                    e = customer_list.get('errors')
                _logger.info("Exception occured: %s", e)
                raise exceptions.UserError(_("Error Occured: %s") % e)

    def _process_addresses(self,update_values,values):
        ############Default Address Starts####################################
        if values.get('default_address') or values.get('addresses'):
            default_address=values.get(
                'default_address') or values.get('addresses')[0]
        else:
            default_address=values
        country=False
        state=False

        if default_address:

            update_values['street']=default_address.get(
                'address1') or ""
            update_values['street2']=default_address.get(
                'address2') or ""
            update_values['city']=default_address.get('city') or ""

            search_domain=[]
            if default_address.get('country_code'):
                search_domain += [('code', '=',
                                default_address.get('country_code'))]
                # country = env['res.country'].sudo().search(
                #     [('code', '=', default_address.get('country_code'))], limit=1)
            elif default_address.get('country'):
                search_domain += [('name', '=',
                                default_address.get('country'))]
                # country = env['res.country'].sudo().search(
                #     [('name', '=', default_address.get('country'))], limit=1)
            country=self.env['res.country'].sudo().search(search_domain, limit=1)
            update_values['country_id']=country.id if country else None
            state_domain=[('country_id', '=', country.id)] if country else []
            if default_address.get('province_code'):
                state_domain += [('code', '=',
                                default_address.get('province_code'))]
                # state = env['res.country.state'].sudo().search(
                #     [('code', '=', default_address.get('province_code'))], limit=1)
            elif default_address.get('province'):
                search_domain += [('name', '=',
                                default_address.get('province'))]
                # state = env['res.country.state'].sudo().search(
                #     [('name', '=', default_address.get('province'))], limit=1)
            state=self.env['res.country.state'].sudo().search(
                state_domain, limit=1)

            update_values['state_id']=state.id if state else None
            update_values['zip']=default_address.get('zip') or ""
