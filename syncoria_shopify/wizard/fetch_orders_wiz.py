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



def get_customer_vals(self, id_key, item, partner_vals):
    customer = item.get('customer', {}).get('default_address')
    partner_vals['name'] = (item.get('customer', {}).get(
        'first_name') or "") + " " + (item.get('customer', {}).get('last_name') or "")
    partner_vals['display_name'] = partner_vals['name']
    # partner_vals['shopify'] = True
    partner_vals['active'] = True
    partner_vals['marketplace'] = True
    partner_vals['marketplace_type'] = 'shopify'
    partner_vals['shopify_id'] = item.get(
        'customer', {}).get(id_key)
    partner_vals['email'] = item.get(
        'customer', {}).get('email')
    partner_vals['phone'] = item.get(
        'customer', {}).get('phone') or ""
    partner_vals['type'] = 'invoice'
    city = ''

    if item.get('addresses'):
        addresses = item.get('addresses')
        if len(addresses) == 1:
            partner_vals['shopify_add_id'] = addresses[0]['id']
        if len(addresses) > 1:
            pass
        city = addresses[0].get('city') or ""
        partner_vals['city'] = city

        country = self.env['res.country'].search(
            [('code', '=', addresses[0]['country_code'])])
        partner_vals['country_id'] = country.id if len(
            country) else False
        state = self.env['res.country.state'].search(
            [('code', '=', addresses[0]['province_code'])])
        partner_vals['state_id'] = state.id if len(
            state) >= 1 else False
        partner_vals['phone'] = addresses[0]['phone'] if addresses[0]['phone'] else False
        partner_vals['zip'] = addresses[0]['zip']
        partner_vals['street'] = addresses[0]['address1'] or ""
        partner_vals['street2'] = addresses[0]['address2'] or ""

    # New Fields
    partner_vals['shopify_accepts_marketing'] = item.get(
        'shopify_accepts_marketing')
    partner_vals['shopify_last_order_id'] = item.get('last_order_id')
    partner_vals['shopify_last_order_name'] = item.get('last_order_name')
    partner_vals['marketing_opt_in_level'] = item.get('marketing_opt_in_level')
    partner_vals['multipass_identifier'] = item.get('multipass_identifier')
    partner_vals['orders_count'] = item.get('orders_count')
    partner_vals['shopify_state'] = item.get('state')
    partner_vals['comment'] = item.get('note')
    partner_vals['shopify_tax_exempt'] = item.get('tax_exempt')
    exempt_ids = []
    if item.get('tax_exempt'):
        for exempt in item.get('tax_exemptions'):
            SpTaxExempt = self.env['shopify.tax.exempt']
            exempt_id = SpTaxExempt.sudo().search(
                [('name', '=', exempt)], limit=1)
            exempt_ids.append(exempt_id.id) if exempt_id else None
    # partner_vals['shopify_tax_exemptions_ids'] = exempt_ids

    partner_vals['shopify_total_spent'] = item.get('total_spent')
    partner_vals['shopify_verified_email'] = item.get('verified_email')
    # Property Payment Method Id
    # instance_id = get_instance_id(self)
    # partner_vals['property_payment_method_id'] = instance_id.marketplace_inbound_method_id.id
    return partner_vals

def get_address_vals(env, address):
    vals = {}
    vals['shopify_add_id'] = address.get('id') or ""
    vals['street'] = address.get('address1') or ""
    vals['street2']=address.get(
    'address2') or ""
    vals['city'] = address.get('city') or ""
    search_domain = []
    if address.get('country_code'):
        search_domain += [('code', '=', address.get('country_code'))]
        # country = env['res.country'].sudo().search(
        #     [('code', '=', address.get('country_code'))], limit=1)
    elif address.get('country'):
        search_domain += [('name', '=', address.get('country'))]
        # country = env['res.country'].sudo().search(
        #     [('name', '=', address.get('country'))], limit=1)
    country = env['res.country'].sudo().search(search_domain, limit=1)
    vals['country_id'] = country.id if country else None
    state_domain = [('country_id', '=', country.id)] if country else []
    if address.get('province_code'):
        state_domain += [('code', '=', address.get('province_code'))]
    # state = env['res.country.state'].sudo().search(
    #     [('code', '=', address.get('province_code'))], limit=1)
    elif address.get('province'):
        search_domain += [('name', '=', address.get('province'))]
    # state = env['res.country.state'].sudo().search(
    #     [('name', '=', address.get('province'))], limit=1)
    state = env['res.country.state'].sudo().search(state_domain, limit = 1)
    vals['state_id']=state.id if state else None
    vals['zip']=address.get('zip') or ""
    return vals


class OrderFetchWizard(models.Model):
    _inherit = 'order.fetch.wizard'

    date_from = fields.Date('From')
    date_to = fields.Date('To')
    order_status = fields.Selection([
            ('any', 'All'),
            ('open', 'Opened'),
            ('closed', 'Closed'),
            ('cancelled', 'Cancelled')
        ], string="Order Status",required=True,default='any')

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
            if self.instance_id:
                marketplace_instance_id =self.instance_id
            else:
                marketplace_instance_id = self.env['marketplace.instance'].sudo().search([('id','=',marketplace_instance_id[0])])
        return marketplace_instance_id

    def shopify_find_customer_id(self, order, ids, partner_vals, main=False):
        # order-->order
        # main-->True: Fetch Customers
        # main-->False: Fetch Orders

        item = order if main else order
        cr = self._cr
        id_key = 'id'
        item_id_key = item.get(id_key) if main else order.get(
            'customer', {}).get('id')
        res = None
        if item_id_key and \
                str(item_id_key) in ids:
            cr.execute("select id from res_partner "
                       "where shopify_id=%s",
                       (str(item_id_key),))
            res = cr.fetchone()
            return res and res[0] or None
        else:
            if not main:
                try:
                    partner_vals = get_customer_vals(
                        self, id_key, item, partner_vals)
                except Exception as e:
                    _logger.warning("\nshopify_find_customer_id===>" + str(e))

            child_ids = []
            if main:
                res_partner = self.env['res.partner'].sudo()
                partner_id = res_partner.search(
                    [('email', '=', item.get('email'))], limit=1)

                _logger.warning("\Partner with Email===>>>%s exists" %
                                (item.get('email')))
                if partner_id:
                    # Need to check Customer Addresses
                    self._process_customer_addresses(partner_id, item)
                    return partner_id.id

                
                partner_vals = ShopifyCustomer(item, self.env)._partner_vals
                if 'child_ids' in partner_vals:
                    child_ids = partner_vals.get('child_ids')
                    del(partner_vals['child_ids'])
            
            if partner_vals.get('shopify_id'):
                query_cols = self.fetch_query(partner_vals)
                query_str = "insert into res_partner (" + \
                            query_cols + ") values %s RETURNING id"
                cr.execute(query_str, (tuple(partner_vals.values()),))
                res = cr.fetchone()

                if res:
                    partner = self.env['res.partner'].sudo().search([('id', '=', res[0])])
                    self._process_customer_tags(partner,item)
                    if len(child_ids) > 0:
                        _logger.info("Partner ===>>>",partner )
                        partner.write({'child_ids':child_ids})


        return res and res[0] or None


    def _process_customer_tags(self,partner_id,values):
        if values.get("tags"):
            splited_tags = values.get("tags").split(',')
            res_partner_cat = self.env['res.partner.category']
            for tags in splited_tags:
                existing_tags = res_partner_cat.search([
                    ("name","=",tags),
                    ("parent_id","=",self.env.ref("syncoria_shopify.shopify_tag").id)
                ],limit=1)
                if existing_tags:
                    partner_id.write({'category_id' : [(4, existing_tags.id)]})
                else:
                    # new_tag=res_partner_cat.create({"name":tags,"color":1,"active":True,"parent_id":env.ref("syncoria_shopify.shopify_tag").id})
                    # self._partner_vals['category_id'] = new_tag.id
                    if tags!="":
                        partner_id.write({'category_id': [(0,0, {"name":tags,"color":1,"active":True,"parent_id":self.env.ref("syncoria_shopify.shopify_tag").id})]})

    def fetch_query(self, vals):
        """constructing the query, from the provided column names"""
        query_str = ""
        if not vals:
            return
        for col in vals:
            query_str += " " + str(col) + ","
        return query_str[:-1]

    def get_customer_id(self, sp_order_dict):
        res_partner = self.env['res.partner'].sudo()
        partner_id = False
        partner_invoice_id = False
        partner_shipping_id = False

        if sp_order_dict.get('customer'):
            customer = sp_order_dict.get('customer')
            shopify_id = customer.get('id')
            if shopify_id:
                domain = [('shopify_instance_id', '=' , self.instance_id.id)]
                domain += [('shopify_id', '=' , shopify_id)]
                domain += [('marketplace_type', '=' , 'shopify')]
                partner_id = res_partner.search(domain, limit=1)

                customer_vals = self.shopify_customer(customer, self.env, shipping=False)
                if not partner_id and customer.get('email'):
                    domain = [('email', '=' , customer.get('email'))]
                    partner_id = res_partner.search(domain, limit=1)
                if partner_id and customer_vals:
                    partner_id.write(customer_vals)
                else:
                    partner_id = res_partner.create(customer_vals)

                if partner_id:
                    partner_invoice_id = self.get_partner_invoice_id(sp_order_dict, partner_id)
                    partner_shipping_id = self.get_partner_shipping_id(sp_order_dict, partner_id)

            try:
                self._cr.commit()
            except Exception as e:
                _logger.warning("Exception-{}".format(e.args))
        return partner_id, partner_invoice_id, partner_shipping_id

    def shopify_customer(self, values, env, shipping=False):
        customer={}
        customer['name']=(values.get(
            'first_name') or "") + " " + (values.get('last_name') or "")
        customer['display_name']=customer['name']
        customer['phone']=values.get('phone') or ""
        customer['email']=values.get('email') or ""
        customer['shopify_id']=values.get('id') or ""
        customer['marketplace_type']='shopify'
        customer['active']=True
        customer['type']='contact'
        customer['shopify_accepts_marketing']=values.get(
            'shopify_accepts_marketing')
        customer['shopify_last_order_id']=values.get(
            'last_order_id')
        customer['shopify_last_order_name']=values.get(
            'last_order_name')
        customer['marketing_opt_in_level']=values.get(
            'marketing_opt_in_level')
        customer['multipass_identifier']=values.get(
            'multipass_identifier')
        customer['orders_count']=values.get('orders_count')
        customer['shopify_state']=values.get('state')
        customer['comment']=values.get('note')
        customer['shopify_tax_exempt']=values.get('tax_exempt')
        exempt_ids=[]
        if values.get('tax_exempt'):
            for exempt in values.get('tax_exemptions'):
                SpTaxExempt=self.env['shopify.tax.exempt']
                exempt_id=SpTaxExempt.sudo().search(
                    [('name', '=', exempt)], limit=1)
                exempt_ids.append(exempt_id.id) if exempt_id else None
            # customer['shopify_tax_exemptions_ids'] = exempt_ids

        customer['shopify_total_spent']=values.get(
            'total_spent')
        customer['shopify_verified_email']=values.get(
            'verified_email')


        if values.get('default_address') or values.get('addresses'):
            default_address=values.get(
                'default_address') or values.get('addresses')[0]
        else:
            default_address=values
        country=False
        state=False

        if default_address:
            # if default_address.get('company'):
            #     company=env['res.partner'].sudo().search(
            #         [('name', '=', default_address.get('company'))], limit=1)
            #     customer['company_id']=company.id if company else None
            #     customer['company_name']=default_address.get(
            #         'company') or ""

            customer['street']=default_address.get(
                'address1') or ""
            customer['street2']=default_address.get(
                'address2') or ""
            customer['city']=default_address.get('city') or ""

            search_domain=[]
            if default_address.get('country_code'):
                search_domain += [('code', '=',
                                default_address.get('country_code'))]

            elif default_address.get('country'):
                search_domain += [('name', '=',
                                default_address.get('country'))]
            country=env['res.country'].sudo().search(search_domain, limit=1)
            customer['country_id']=country.id if country else None
            state_domain=[('country_id', '=', country.id)] if country else []
            if default_address.get('province_code'):
                state_domain += [('code', '=',
                                default_address.get('province_code'))]

            elif default_address.get('province'):
                search_domain += [('name', '=',
                                default_address.get('province'))]

            state=env['res.country.state'].sudo().search(
                state_domain, limit=1)

            customer['state_id']=state.id if state else None
            customer['zip']=default_address.get('zip') or ""

        return customer


    def get_partner_invoice_id(self, sp_order_dict, partner_id):
        res_partner = self.env['res.partner'].sudo()
        partner_invoice_id = partner_id
        if sp_order_dict.get('billing_address'):
            billing_address = sp_order_dict.get('billing_address', {})

            partner_invoice_id = partner_id.child_ids.filtered(lambda l:l.type == 'invoice')
            if partner_invoice_id:
                country_domain = [('name', '=', billing_address.get(
                    'country'))] if billing_address.get('country') else []
                country_domain += [('name', '=', billing_address.get('province'))
                                    ] if billing_address.get('province') else country_domain
                country_id = self.env['res.country'].sudo().search(
                    country_domain, limit=1)

                state_domain = [('country_id', '=', country_id.id)
                                ] if country_id else []
                state_domain += [('name', '=', billing_address.get('province'))
                                ] if billing_address.get('province') else state_domain
                state_id = self.env['res.country.state'].sudo().search(
                    state_domain, limit=1)

                partner_invoice_id.write({
                    'name': billing_address.get('name', None),
                    'street': billing_address.get('address1'),
                    'street2': billing_address.get('address2'),
                    'zip': billing_address.get('zip'),
                    'country_id': country_id.id,
                    'state_id': state_id.id,
                    'city': billing_address.get('city'),
                    'parent_id': partner_id.id,
                    'property_account_receivable_id' : partner_id.property_account_receivable_id.id,
                    'property_account_payable_id' : partner_id.property_account_payable_id.id,
                    'type': 'invoice'
                })


            if not partner_invoice_id:
                partner_invoice_id = self._match_or_create_address(
                    partner_id, sp_order_dict.get('billing_address'), 'invoice')

            if partner_id and partner_invoice_id and not partner_invoice_id.property_account_receivable_id:
                partner_invoice_id.property_account_receivable_id = partner_id.property_account_receivable_id.id
            if partner_id and partner_invoice_id and not partner_invoice_id.property_account_payable_id:
                partner_invoice_id.property_account_payable_id = partner_id.property_account_payable_id.id
        try:
            self._cr.commit()
        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))
        return partner_invoice_id

    def get_partner_shipping_id(self, sp_order_dict, partner_id):
        partner_shipping_id = partner_id
        if sp_order_dict.get('shipping_address'):
            shipping_address = sp_order_dict.get('shipping_address', {})

            partner_shipping_id = partner_id.child_ids.filtered(lambda l:l.type == 'delivery')
            if partner_shipping_id:
                country_domain = [('name', '=', shipping_address.get(
                    'country'))] if shipping_address.get('country') else []
                country_domain += [('name', '=', shipping_address.get('province'))
                                    ] if shipping_address.get('province') else country_domain
                country_id = self.env['res.country'].sudo().search(
                    country_domain, limit=1)

                state_domain = [('country_id', '=', country_id.id)
                                ] if country_id else []
                state_domain += [('name', '=', shipping_address.get('province'))
                                ] if shipping_address.get('province') else state_domain
                state_id = self.env['res.country.state'].sudo().search(
                    state_domain, limit=1)

                partner_shipping_id.write({
                    'name': shipping_address.get('name', None),
                    'street': shipping_address.get('address1'),
                    'street2': shipping_address.get('address2'),
                    'zip': shipping_address.get('zip'),
                    'country_id': country_id.id,
                    'state_id': state_id.id,
                    'city': shipping_address.get('city'),
                    'parent_id': partner_id.id,
                    'property_account_receivable_id' : partner_id.property_account_receivable_id.id,
                    'property_account_payable_id' : partner_id.property_account_payable_id.id,
                    'type': 'invoice'
                })

                
            if not partner_shipping_id:
                partner_shipping_id = self._match_or_create_address(
                    partner_id, sp_order_dict.get('shipping_address'), 'delivery')

            if partner_id and partner_shipping_id and not partner_shipping_id.property_account_receivable_id:
                partner_shipping_id.property_account_receivable_id = partner_id.property_account_receivable_id.id
            if partner_id and partner_shipping_id and not partner_shipping_id.property_account_payable_id:
                partner_shipping_id.property_account_payable_id = partner_id.property_account_payable_id.id
        try:
            self._cr.commit()
        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))
        return partner_shipping_id



    def shopify_fetch_orders(self, kwargs=None):
        """Fetch Orders"""
        PartnerObj = self.env['res.partner'].sudo()
        OrderObj = self.env['sale.order'].sudo()
        ProductObj = self.env['product.product'].sudo()
        CarrierObj = self.env['delivery.carrier'].sudo()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        AccMove = self.env['account.move'].sudo()
        all_shopify_orders = self.env['sale.order'].sudo()

        cr = self._cr
        if not kwargs:
            marketplace_instance_id = self._get_instance_id()
        else:
            marketplace_instance_id = kwargs.get("marketplace_instance_id")

        version = marketplace_instance_id.marketplace_api_version or '2021-04'
        url = marketplace_instance_id.marketplace_host + \
            '/admin/api/%s/orders.json' % version
        refund_url = url
        
        tz_offset = '-00:00'
        if self.env.user and self.env.user.tz_offset:
            tz_offset = self.env.user.tz_offset

        if self.date_from and not self.date_to:
            url += '?created_at_min=%s' % self.date_from.strftime(
                "%Y-%m-%dT00:00:00" + tz_offset)
            refund_url += '?updated_at_min=%s' % self.date_from.strftime(
                "%Y-%m-%dT00:00:00" + tz_offset)
        if not self.date_from and self.date_to:
            url += '?created_at_max=%s' % self.date_to.strftime(
                "%Y-%m-%dT23:59:59" + tz_offset)
            refund_url += '?updated_at_max=%s' % self.date_to.strftime(
                "%Y-%m-%dT23:59:59" + tz_offset)
        if self.date_from and self.date_to:
            url += '?created_at_min=%s' % self.date_from.strftime(
                "%Y-%m-%dT00:00:00" + tz_offset)
            url += '&created_at_max=%s' % self.date_to.strftime(
                "%Y-%m-%dT23:59:59" + tz_offset)
            refund_url += '?updated_at_min=%s' % self.date_from.strftime(
                "%Y-%m-%dT00:00:00" + tz_offset)
            refund_url += '&updated_at_max=%s' % self.date_to.strftime(
                "%Y-%m-%dT23:59:59" + tz_offset)
        if not self.date_from and not self.date_to:
            url += '?created_at_min=%s' % fields.Datetime.now().strftime(
                "%Y-%m-%dT00:00:00" + tz_offset)
            url += '&created_at_max=%s' % fields.Datetime.now().strftime(
                "%Y-%m-%dT23:59:59"  + tz_offset)
            refund_url += '?updated_at_min=%s' % fields.Datetime.now().strftime(
                "%Y-%m-%dT00:00:00" + tz_offset)
            refund_url += '&updated_at_max=%s' % fields.Datetime.now().strftime(
                "%Y-%m-%dT23:59:59" + tz_offset)

        _logger.info("url===>>>>{}".format(url))
        # Example: https://linus-sandbox.myshopify.com/admin/api/2022-01/orders.json?created_at_min=2022-04-05T00:00:00%2B0600&created_at_max=2022-04-05T23:59:59%2B0600


        # Request Parameters
        type_req = 'GET'
        params = {"limit": 250}
        # if self.order_status:
        params.update({"status":self.order_status})

        orders = []
        headers = {
            'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password}
        while True:
            fetched_orders, next_link = self.env['marketplace.connector'].shopify_api_call(headers=headers,
                                                                                           url=url, type=type_req,
                                                                                           marketplace_instance_id=marketplace_instance_id,
                                                                                           params=params)
            try:
                orders += fetched_orders['orders']
                if next_link:
                    if next_link.get("next"):
                        url = next_link.get("next").get("url")
                        if params.get('status'):
                            del(params['status'])

                    else:
                        break
                else:
                    break
            except Exception as e:
                _logger.info("Exception occured: %s", e)
                raise exceptions.UserError(_("Error Occured %s") % e)

        """
        FETCH REFUNDS IN THE DATE RANGE
        """
        while True:
            refund_url += '&financial_status=refunded,partially_refunded&status=any'
            fetched_orders, next_link = self.env['marketplace.connector'].shopify_api_call(headers=headers,
                                                                                           url=refund_url, type=type_req,
                                                                                           marketplace_instance_id=marketplace_instance_id,
                                                                                           params=params)
            try:
                _logger.info(refund_url)
                _logger.info("<-------------  REFUNDS SHOPIFY TODAY ------------->")
                _logger.info(fetched_orders['orders'])
                orders += fetched_orders['orders']
                if next_link:
                    if next_link.get("next"):
                        url = next_link.get("next").get("url")
                        if params.get('status'):
                            del(params['status'])

                    else:
                        break
                else:
                    break
            except Exception as e:
                _logger.info("Exception occured: %s", e)
                raise exceptions.UserError(_("Error Occured %s") % e)

        order_list = {"orders": orders}

        if url and order_list:
            _logger.info("\nurl >>>>>>>>>>>>>>>>>>>>>>" + str(url) +
                         "\nOrder #:--->" + str(len(order_list.get('orders'))))

        try:
            log_msg = ''
            error_msg = ''
            sp_orders = order_list['orders']

            feed_order_list = []
            for i in sp_orders:
                feed_order_id, feed_log_msg, feed_error_msg = self.create_feed_orders(i)
                log_msg += feed_log_msg
                error_msg += feed_error_msg
                if feed_order_id:
                    feed_order_list += feed_order_id.ids

                    process_log_msg, process_error_msg = feed_order_id.process_feed_order()
                    log_msg += process_log_msg
                    error_msg += process_error_msg




            try:
                print("log_msg ===>>>{}".format(log_msg))
                print("error_msg ===>>>{}".format(error_msg))
                if self.instance_id:
                    log_id = self.env['marketplace.logging'].sudo().create({
                        'name' : self.env['ir.sequence'].next_by_code('marketplace.logging'),
                        'create_uid' : self.env.user.id,
                        'marketplace_type' : self.instance_id.marketplace_instance_type,
                        'shopify_instance_id' : self.instance_id.id,
                        'level' : 'info',
                        'summary' : log_msg.replace('<br>','').replace('</br>','\n'),
                        'error' : error_msg.replace('<br>','').replace('</br>','\n'),
                    })
                    log_id._cr.commit()
                    print("log_id ===>>>{}".format(log_id))
            except Exception as e:
                print("Exception-{}".format(e.args))


        except Exception as e:
            _logger.warning("Exception occured %s", e)
            raise exceptions.UserError(_("Error Occured:\n %s") % e)



        if 'call_button' in str(request.httprequest):
            return {
                'name': ('Shopify Orders'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'sale.order',
                'view_id': False,
                'domain': [('marketplace_type', '=', 'shopify')],
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload'
            }

    def _get_delivery_line(self, i, order_vals, marketplace_instance_id):
        ProductObj = self.env['product.product'].sudo()
        service = self.env.ref('syncoria_shopify.shopify_shipping')
        if i.get('shipping_lines'):
            # Find shipping service from Shopify Order\
            for ship_line in i.get('shipping_lines'):
                domain = [('default_code', '=', ship_line['code'])]
                service = ProductObj.search(
                    domain, limit=1) if not service else service
                if len(service) == 0:
                    ship_values = self._shopify_get_ship(
                        ship_line, marketplace_instance_id)
                    service = ProductObj.create(ship_values)

                shipping_name = ship_line.get('title')
                product_name = ship_line.get('title')
                if ship_line.get('carrier_identifier'):
                    print("CARIIER IDENTIFIER",
                          ship_line.get('carrier_identifier'))

                ship_tax = []
                if ship_line.get('tax_lines') and len(ship_line.get('tax_lines')) > 0:
                    ship_tax = self._shopify_get_taxnames(
                        ship_line.get('tax_lines'))
                    # disc_per = 0
                    # if ship_line.get("discounted_price") != ship_line.get("price"):
                    #     if float(line.get("discounted_price")) != 0:
                    #         discount = float(
                    #             line.get("price")) - float(line.get("discounted_price"))
                    #         disc_per = (
                    #             discount/line.get("price")) * 100
                
                #####################################################################################
                #TO DO: Compute Price from Pricelist
                delivery_price =  ship_line.get('price')
                pricelist_currency = marketplace_instance_id.pricelist_id.currency_id.name
                shop_currency_code = ship_line.get('price_set', {}).get('shop_money',{}).get('currency_code')
                pre_currency_code = ship_line.get('price_set', {}).get('presentment_money',{}).get('currency_code')
                if pricelist_currency and shop_currency_code:
                    _logger.info("\npricelist_currency-{}\nshop_currency_code-{}\npre_currency_code-{}".format(pricelist_currency, shop_currency_code, pre_currency_code))
                    if pricelist_currency == shop_currency_code:
                        _logger.info("Shop and Pricelist Currency Matches")
                    else:
                        _logger.info("Shop and Pricelist Currency Not Matching")
                        delivery_price = self.compute_price_unit(service, delivery_price)
                        #Convert Price to Pricelist Currency
                        delivery_price = marketplace_instance_id.pricelist_id.currency_id.rate*float(delivery_price)
                
                _logger.info("Shipping Pirce Unit-{}".format(delivery_price))
                #####################################################################################
                temp = {
                    'product_id': service.id,
                    'product_uom_qty': 1,
                    'price_unit': delivery_price,
                    # 'discount': disc_per,
                    'tax_id': [(6, 0, ship_tax)],
                }
                order_vals['order_line'].append((0, 0, temp))
                order_vals['carrier_id'] = False
                order_vals['shopify_carrier_service'] = False
        else:
            temp = {
                'product_id': service.id,
                'product_uom_qty': 1,
                'price_unit': 0.00,
                'tax_id': [(6, 0, [])],
            }
            order_vals['order_line'].append((0, 0, temp))
        return order_vals

    def process_discount_codes(self, sp_order, order_vals):
        VariantObj = self.env['product.product'].sudo()
        total_discount = 0
        # total_discount = -float(sp_order.get('current_total_discounts')
        #                         ) if sp_order.get('current_total_discounts') else 0
        if total_discount == 0:
            if len(sp_order.get('discount_codes')) > 0:
                _logger.info("discount_codes===>>>" +
                             str(sp_order.get('discount_codes')))
                for disc in sp_order.get('discount_codes'):
                    if disc['type'] != 'percentage':
                        total_discount -= float(disc.get('amount'))

        service = self.env.ref('syncoria_shopify.shopify_discount')
        service = VariantObj.search(
            [('name', '=', 'Discount')], limit=1) if not service else service
        if service:
            #####################################################################################
            #TO DO: Compute Price from Pricelist
            #####################################################################################
            temp = {
                'product_id': service.id,
                'product_uom_qty': 1,
                'price_unit': total_discount,
                'tax_id': [(6, 0, [])],
            }
            print("temp--->", temp)
            order_vals['order_line'].append((0, 0, temp))
        return order_vals


    def _get_inv_vals(self, order_id, sp_order):
        inv_vals = {}
        mkplc_id = self._get_instance_id()
        inv_vals.update({
            "ref": "",
            "move_type": "out_invoice",
            "narration": "",
            "currency_id": order_id.currency_id.id,
            "campaign_id": order_id.campaign_id.id,
            "medium_id": order_id.medium_id.id,
            "source_id": order_id.source_id.id,
            "user_id": order_id.user_id.id,
            "invoice_user_id": order_id.user_id.id,
            "team_id": order_id.team_id.id,
            "partner_id": order_id.partner_id.id,
            "partner_shipping_id": order_id.partner_shipping_id.id,
            "fiscal_position_id": order_id.fiscal_position_id.id,
            # "partner_bank_id": order_id.partner_bank_id.id,
            "journal_id": mkplc_id.marketplace_journal_id.id,
            "invoice_origin": order_id.name,
            "invoice_payment_term_id": mkplc_id.payment_term_id.id,
            "payment_reference": False,
            "transaction_ids": [(6, 0, [])],
            "company_id": order_id.company_id.id,
            "invoice_incoterm_id": False
        })
        inv_vals['invoice_line_ids'] = []

        for line in order_id.order_line:
            #####################################################################################
            #TO DO: Compute Price from Pricelist
            #####################################################################################
            inv_vals['invoice_line_ids'].append(
                (0, 0,
                 {
                     "display_type": False,
                     "sequence": 0,
                     "name": line.name,
                     "product_id": line.product_id.id,
                     "product_uom_id": line.product_id.uom_id.id,
                     "quantity": line.product_qty,
                     "discount": line.discount,
                     "price_unit": line.price_unit,
                     "tax_ids": [(6, 0, line.tax_id.ids)],
                     "analytic_account_id": False,
                     "analytic_tag_ids": [(6, 0, [])],
                     "sale_line_ids": [(4, 81)]
                 })
            )

        self.env['account.move'].sudo().create(inv_vals)

    # def _shopify_process_payments(self, move_id, sp_order):
    #     payments = False
    #     mkplc_id = self._get_instance_id()
    #     AccPay = self.env['account.payment'].sudo()
    #     print("move_id.payment_id===>>>" + str(move_id.payment_id))
    #     payments = {}
    #     if sp_order.get('payment_details') and move_id.amount_residual > 0:
    #         payment_vals_list = self._shopify_payment_vals(move_id, sp_order)
    #         _logger.info("" + pprint.pformat(payment_vals_list))
    #         pay_domain = [('ref', '=', move_id.name)]
    #         pay_domain += [('amount', '=', move_id.amount_residual)]
    #         payment = AccPay.search(pay_domain, limit=1)
    #         if not payment:
    #             payment = AccPay.create(payment_vals_list)
    #             _logger.info("Payment Created- %s" % (payment))

    #         if sp_order.get('financial_status') in ['authorized', 'paid']:
    #             if not payment.line_ids:
    #                 if payment.payment_type == 'inbound':
    #                     payment.write({
    #                         'line_ids': [(0, 0, {
    #                             'name': 'Customer Payment %s %s-%s' % (payment.amount, payment.currency_id.symbol, payment.date),
    #                             'account_id': mkplc_id.debit_account_id.id,
    #                             'debit': payment.amount,
    #                             'credit': 0,
    #                             'quantity': 1,
    #                             'date_maturity': payment.date,
    #                             'move_id': payment.move_id.id,
    #                         }),

    #                         (0, 0, {
    #                             'name': 'Customer Payment %s %s-%s' % (payment.amount, payment.currency_id.symbol, payment.date),
    #                             'account_id': mkplc_id.credit_account_id.id,
    #                             'debit': 0,
    #                             'credit': payment.amount,
    #                             'quantity': 1,
    #                             'date_maturity': payment.date,
    #                             'move_id': payment.move_id.id,
    #                         })

    #                         ]
    #                     })
    #             payment.action_post() if payment.state == 'draft' else None
    #             # Error for order id: sale.order(34,)- ('You need to add a line before posting.',)
    #             if payment.state == 'posted':
    #                 move_id.sudo().write({
    #                     'payment_id': payment.id,
    #                     'payment_state': 'paid',
    #                 })
    #                 payment.write({'is_reconciled': True})

    #     print("move_id.payment_id===>>>" + str(move_id.payment_id))
    #     print("move_id.payment_id.is_reconciled===>>>" +
    #           str(move_id.payment_id.is_reconciled))
    #     if move_id.payment_id:
    #         if move_id.payment_id.amount == move_id.amount_total and move_id.payment_id.state == 'posted':
    #             if move_id.payment_state != 'paid':
    #                 move_id.write({
    #                     'payment_state': 'paid',
    #                     'amount_residual': 0,
    #                     'payment_reference':  move_id.payment_id.name
    #                 })
    #             move_id.payment_id.sudo().write({
    #                 'is_reconciled': True,
    #                 # 'move_id':move_id.id
    #             })  # Please define a payment method on your payment.

    #     if sp_order.get('refunds'):
    #         """Create a Invoice Credit Note"""
    #         move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=move_id.ids).create({
    #             'date': fields.Datetime.now(),
    #             'reason': 'no reason',
    #             'refund_method': 'refund',
    #         })
    #         reversal = move_reversal.reverse_moves()
    #         reverse_move = self.env['account.move'].browse(reversal['res_id'])
    #         _logger.info("Reversal Move--->", reverse_move)

    #         for refund in sp_order.get('refunds'):
    #             for refund_trx in refund.get('transactions'):
    #                 """Create Payment Refunds"""
    #                 refund_tx = self._shopify_refund_vals(refund_trx)
    #                 refunds_vals_list = self._shopify_payment_vals(
    #                     reverse_move, refund_trx)
    #                 refund_trxs = self.env['account.payment'].create(
    #                     payment_vals_list)
    #     return payments

    def _shopify_payment_vals(self, move_id, sp_order):
        instance_id = self._get_instance_id()
        journal_id = move_id.journal_id.id or instance_id.marketplace_payment_journal_id.id
        vals = {}
        instance_id = self._get_instance_id()
        journal_id = instance_id.marketplace_payment_journal_id.id
        payment_method_id = self.env['account.payment.method'].sudo().search([
            ('name', '=', 'Manual'),
            ('payment_type', '=', 'inbound'),
        ], limit=1)

        vals = {
            'date': fields.Datetime.now(),
            # 'extract_date' : move_id.extract_date,
            'amount': move_id.amount_total,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'ref': move_id.name,
            'journal_id': journal_id,
            'currency_id': 4,
            'partner_id': move_id.partner_id.id,
            'partner_bank_id': False,
            'payment_method_id': payment_method_id.id,
            # 'destination_account_id': 4,
            'payment_token_id': False,
            'invoice_origin': move_id.invoice_origin,
            'marketplace_type': 'shopify',
            # 'move_id': move_id.id,# You cannot edit the journal of an account move if it has been posted once.

        }
        for key, value in sp_order.get('payment_details').items():
            vals.update({'shopify_' + str(key) + "": str(value)})
        vals.update({
            'shopify_payment_gateway_names': sp_order.get('payment_gateway_names'),
        })
        return vals

    def _shopify_refund_vals(self, move_id, refund):
        instance_id = self._get_instance_id()
        journal_id = move_id.journal_id.id or instance_id.marketplace_journal_id.id
        payment_method_id = self.env['account.payment.method'].sudo().search([
            ('name', '=', 'Manual'),
            ('payment_type', '=', 'outbound')])
        instance_id = self._get_instance_id()
        journal_id = instance_id.marketplace_journal_id.id or move_id.journal_id.id
        payment_method_id = self.env['account.payment.method'].sudo().search([
            ('name', '=', 'Manual'),
            ('payment_type', '=', 'outbound'),
        ], limit=1)
        vals = {}
        vals.update({
            'shopify_id': refund.get('id'),
            'date': fields.Datetime.now(),
            'journal_id': journal_id,
            'move_id': move_id.id,
            'move_type': 'out_refund',
            'partner_type': 'customer',
            'payment_method_id': payment_method_id.id,
            'payment_type': 'outbound',
            # 'payment_reference': 'inbound',
            # 'payment_transaction_id': 'inbound',
            # 'payment_token_id': False,
            'partner_id': move_id.partner_id.id,
            'amount': refund.get('amount'),
            'invoice_origin': move_id.invoice_origin,
            'ref': move_id.name,
            'shopify_payment_gateway_names': refund.get('gateway'),
            'destination_account_id': 4,
        })
        return vals

    def _shopify_get_ship(self, ship_line, ma_ins_id):
        ship_value = {}
        ship_value['name'] = ship_line.get('title')
        ship_value['sale_ok'] = False
        ship_value['purchase_ok'] = False
        ship_value['type'] = 'service'
        ship_value['default_code'] = ship_line.get('code')
        categ_id = self.env['product.category'].sudo().search(
            [('name', '=', 'Deliveries')], limit=1)
        ship_value['categ_id'] = categ_id.id
        ship_value['company_id'] = ma_ins_id.company_id.id
        ship_value['responsible_id'] = ma_ins_id.user_id.id
        return ship_value

    def _shopify_get_taxnames(self, tax_lines):
        tax_names = []
        for tax_id in tax_lines:
            search_domain = [
                ('name', 'like', tax_id['title']),
                ('amount', '=', tax_id['rate'] * 100),
                ('type_tax_use', '=', 'sale'),
                ('marketplace_type', '=', 'shopify'),
            ]
            Tax = self.env['account.tax']
            tax_ob = Tax.sudo().search(search_domain, limit=1)
            if not tax_ob:
                Tax.sudo().create({
                    'name': tax_id['title'],
                    'amount': tax_id['rate'] * 100,
                    'type_tax_use': 'sale',
                    'marketplace_type': 'shopify',
                    'shopify': True,
                })

            tax_names.append(tax_ob.id)
        return tax_names

    def shopify_update_orders(self):
        """Update Orders on Shopify"""
        print("shopify_update_orders")
        marketplace_id = self._get_instance_id()
        PartnerObj = self.env['res.partner'].sudo()
        OrderObj = self.env['sale.order'].sudo()
        ProductObj = self.env['product.product'].sudo()
        CarrierObj = self.env['delivery.carrier'].sudo()

        # Find all the orders that needs to be updated
        # Find api to update the orders
        # POST /admin/api/2021-04/orders/{order_id}/cancel.json
        # Cancels an order
        # POST /admin/api/2021-04/orders.json
        # Creates an order
        # PUT /admin/api/2021-04/orders/{order_id}.json
        # Updates an order
        # DELETE /admin/api/2021-04/orders/{order_id}.json
        # Deletes an order

    def shopify_push_tracking(self):
        SaleOrder = self.env['sale.order'].sudo()
        StkPicking = self.env['stock.picking'].sudo()
        marketplace_instance_id = self._get_instance_id()
        current_date = fields.Datetime.now()
        _logger.info("current_date#===>>>" + str(current_date))
        start_date = current_date.replace(
            hour=0, minute=0, second=0, microsecond=0)
        end_date = current_date.replace(
            hour=23, minute=59, second=59, microsecond=999999)
        _logger.info("start_date#===>>>" + str(start_date))
        _logger.info("end_date#===>>>" + str(end_date))
        log_msg = ''

        if marketplace_instance_id.marketplace_instance_type == 'shopify':
            sale_domain = [('state', 'in', ('sale', 'done')),
                           ('shopify_track_updated', '=', False),
                           ('date_order', '>=', start_date),
                           ('date_order', '<=', end_date)
                           ]
            sale_ids = SaleOrder.search(sale_domain)

            _logger.info("Sale#===>>>" + str(sale_ids))
            for sale_id in sale_ids:
                """Step: 1. Find all Pickings for sale Order"""
                pick_domain = [
                    ('state', '=', 'done'),
                    ('shopify_track_updated', '=', False),
                    ('origin', '=', sale_id.name)]
                pickings = StkPicking.search(pick_domain)
                _logger.info("pickings#===>>>" + str(pickings))
                """Step: 2. If Picking == 1: Update Tracking Number"""
                if len(pickings) == 1:
                    msg = _("Push Tracking for Sale Order-%s, Picking-%s Starts" %
                            (sale_id.name, pickings.name))
                    _logger.info(msg)
                    log_msg += "\n" + msg
                    response = pickings.create_shopify_fulfillment()
                    msg = _("Push Tracking for Sale Order-%s, Picking-%s Ends" %
                            (sale_id.name, pickings.name))
                    _logger.info(msg)
                    log_msg += "\n" + msg
                """Step: 2. If Picking  > 1: Do nothing"""
                if len(pickings) > 1:
                    msg = _("Tracking cannot be updated for Sale Order-%s" %
                            (sale_id.name))
                    _logger.warning(msg)
                    log_msg += "\n" + msg




    def _match_or_create_address(self, partner, checkout, contact_type):
        Partner = self.env['res.partner']
        street = checkout.get('address1')
        street2 = checkout.get('address2')
        azip = checkout.get('zip')
        if partner:
            # delivery = partner.child_ids.filtered(
            #     lambda c: c.street == street or c.street2 == street2 or c.zip == azip)
            delivery = partner.child_ids.filtered(
                lambda c: (c.street == street or c.street2 == street2 or c.zip == azip) and c.type == contact_type and c.phone == checkout.get('phone'))

            country_domain = [('name', '=', checkout.get(
                'country'))] if checkout.get('country') else []
            country_domain += [('name', '=', checkout.get('province'))
                                ] if checkout.get('province') else country_domain
            country_id = self.env['res.country'].sudo().search(
                country_domain, limit=1)

            state_domain = [('country_id', '=', country_id.id)
                             ] if country_id else []
            state_domain += [('name', '=', checkout.get('province'))
                              ] if checkout.get('province') else state_domain
            state_id = self.env['res.country.state'].sudo().search(
                state_domain, limit=1)

            if not delivery:
                delivery = Partner.sudo().with_context(tracking_disable=True).create({
                    'name': checkout.get('name', None),
                    'street': street,
                    'street2': street2,
                    'zip': azip,
                    'country_id': country_id.id,
                    'state_id': state_id.id,
                    'city': checkout.get('city', None),
                    'parent_id': partner.id,
                    'property_account_receivable_id' : partner.property_account_receivable_id.id,
                    'property_account_payable_id' : partner.property_account_payable_id.id,
                    'type': contact_type
                })
            return delivery[0]
        else:
            return False

    def _process_customer_addresses(self, partner_id, item):
        vals = {}
        if type(item['addresses']) == dict:
            if item.get('addresses'):
                for address in item.get('addresses'):
                    if address.get('default') and partner_id.type == 'invoice':
                        partner_id.write({
                            'shopify_default': True,
                            'shopify_add_id': address.get('id'),
                        })
                    if address.get('default') == False:
                        domain = [('shopify_add_id', '=', address.get('id'))]
                        res_partner = self.env['res.partner']
                        part_id = res_partner.sudo().search(domain, limit=1)
                        if not part_id:
                            add_vals = get_address_vals(self.env, address)
                            add_vals['type'] = 'other'
                            add_vals['parent_id'] = partner_id.id
                            add_vals['property_account_receivable_id'] = partner_id.property_account_receivable_id.id
                            add_vals['property_account_payable_id'] = partner_id.property_account_payable_id.id

                            res_partner.sudo().create(add_vals)
        elif type(item.get('addresses')) == list:
            for address in item['addresses']:
                if address.get('default') and partner_id.type == 'invoice':
                    partner_id.write({
                        'shopify_default': True,
                        'shopify_add_id': address.get('id'),
                    })
                if address.get('default') == False:
                    domain = [('shopify_add_id', '=', address.get('id'))]
                    res_partner = self.env['res.partner']
                    part_id = res_partner.sudo().search(domain, limit=1)
                    if not part_id:
                        add_vals = get_address_vals(self.env, address)
                        add_vals['type']='other'
                        add_vals['parent_id'] = partner_id.id
                        add_vals['property_account_receivable_id'] = partner_id.property_account_receivable_id.id
                        add_vals['property_account_payable_id'] = partner_id.property_account_payable_id.id
                        res_partner.sudo().create(add_vals)

        return vals


    def get_sale_order_vals(self, marketplace_instance_id, customer_id, i):
        order_vals = {}
        partner_invoice_id = False
        partner_shipping_id = False
        if marketplace_instance_id:
            order_vals['warehouse_id'] = marketplace_instance_id.warehouse_id.id if marketplace_instance_id.warehouse_id else None
            order_vals['company_id'] = marketplace_instance_id.company_id.id or self.env.company.id
            order_vals['user_id'] = marketplace_instance_id.user_id.id if marketplace_instance_id.user_id else None
            order_vals['fiscal_position_id'] = marketplace_instance_id.fiscal_position_id.id or None
            order_vals['pricelist_id'] = marketplace_instance_id.pricelist_id.id if marketplace_instance_id.pricelist_id else None
            order_vals['payment_term_id'] = marketplace_instance_id.payment_term_id.id if marketplace_instance_id.payment_term_id else None
            order_vals['team_id'] = marketplace_instance_id.sales_team_id.id if marketplace_instance_id.sales_team_id else None
            order_vals['shopify_instance_id'] = marketplace_instance_id.id

            if marketplace_instance_id.sales_team_id:
                order_vals['team_id'] = marketplace_instance_id.sales_team_id.id
            if marketplace_instance_id.user_id:
                order_vals['user_id'] = marketplace_instance_id.user_id.id
            if marketplace_instance_id.payment_term_id:
                order_vals['payment_term_id'] = marketplace_instance_id.payment_term_id.id


        # order_vals['marketplace'] = True
        order_vals['marketplace_type'] = 'shopify'
        order_vals['shopify_instance_id'] = marketplace_instance_id.id
        order_vals['shopify_id'] = str(i['id'])
        order_vals['partner_id'] = customer_id
        order_vals['shopify_status'] = i.get('confirmed')
        order_vals['shopify_order'] = i.get('name')
        order_vals['shopify_financial_status'] = i.get('financial_status')
        order_vals['shopify_fulfillment_status'] = i.get('fulfillment_status')
        order_vals['date_order'] = i.get('created_at')
        if i.get('created_at'):
            order_vals['date_order'] = i.get('created_at').split(
                "T")[0] + " " + i.get('created_at').split("T")[1].split("+")[0].split('-')[0]

        if customer_id:
            customer = self.env['res.partner'].sudo().search([('id', '=', customer_id)], limit=1)
            invoice_id = customer.child_ids.filtered(lambda r: r.type == 'invoice') or customer
            partner_invoice_id = invoice_id[0].id
            shipping_id = customer.child_ids.filtered(lambda r: r.type == 'delivery') or customer
            partner_shipping_id = shipping_id[0].id

        order_vals.update({
            'partner_id': customer_id,
            'partner_invoice_id': partner_invoice_id,
            'partner_shipping_id': partner_shipping_id,
        })
        return order_vals


class ShopifyCustomer:
    def __init__(self, values, env, shipping=False):
        self._partner_vals={}
        self._partner_vals['child_ids'] = []
        self._partner_vals['name']=(values.get(
            'first_name') or "") + " " + (values.get('last_name') or "")
        self._partner_vals['display_name']=self._partner_vals['name']
        self._partner_vals['phone']=values.get('phone') or ""
        self._partner_vals['email']=values.get('email') or ""
        self._partner_vals['shopify_id']=values.get('id') or ""
        self._partner_vals['marketplace_type']='shopify'
        self._partner_vals['active']=True
        self._partner_vals['type']='invoice'
        self._partner_vals['shopify_accepts_marketing']=values.get(
            'shopify_accepts_marketing')
        self._partner_vals['shopify_last_order_id']=values.get(
            'last_order_id')
        self._partner_vals['shopify_last_order_name']=values.get(
            'last_order_name')
        self._partner_vals['marketing_opt_in_level']=values.get(
            'marketing_opt_in_level')
        self._partner_vals['multipass_identifier']=values.get(
            'multipass_identifier')
        self._partner_vals['orders_count']=values.get('orders_count')
        self._partner_vals['shopify_state']=values.get('state')
        self._partner_vals['comment']=values.get('note')
        self._partner_vals['shopify_tax_exempt']=values.get('tax_exempt')
        exempt_ids=[]
        if values.get('tax_exempt'):
            for exempt in values.get('tax_exemptions'):
                SpTaxExempt=env['shopify.tax.exemptions']
                exempt_id=SpTaxExempt.sudo().search(
                    [('name', '=', exempt)], limit=1)
                exempt_ids.append(exempt_id.id) if exempt_id else None
            # self._partner_vals['shopify_tax_exemptions_ids'] = exempt_ids

        self._partner_vals['shopify_total_spent']=values.get(
            'total_spent')
        self._partner_vals['shopify_verified_email']=values.get(
            'verified_email')

        # Handle Company
        # Handle Different Type of Addresses
        self._process_addresses(env, values)

    def _process_addresses(self, env, values):
        ############Default Address Starts####################################
        if values.get('default_address') or values.get('addresses'):
            default_address=values.get(
                'default_address') or values.get('addresses')[0]
        else:
            default_address=values
        country=False
        state=False

        if default_address:
            # self._handle_company(default_address)
            # if default_address.get('company'):
            #     company=env['res.partner'].sudo().search(
            #         [('name', '=', default_address.get('company'))], limit=1)
            #     self._partner_vals['company_id']=company.id if company else None
            #     self._partner_vals['company_name']=default_address.get(
            #         'company') or ""

            self._partner_vals['street']=default_address.get(
                'address1') or ""
            self._partner_vals['street2']=default_address.get(
                'address2') or ""
            self._partner_vals['city']=default_address.get('city') or ""

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
            country=env['res.country'].sudo().search(search_domain, limit=1)
            self._partner_vals['country_id']=country.id if country else None
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
            state=env['res.country.state'].sudo().search(
                state_domain, limit=1)

            self._partner_vals['state_id']=state.id if state else None
            self._partner_vals['zip']=default_address.get('zip') or ""

        # if values.get('addresses'):
        #     if len(values.get('addresses')) > 1:
        #         for address in values.get('addresses'):
        #             if not address.get('default'):
        #                 add_vals = get_address_vals(env, address)
        #                 self._partner_vals['child_ids'].append((0, 0, add_vals))
        ############Default Address Ends####################################


    def _handle_company(self, env, address):
        vals={}
        if address.get('company'):
            domain=[('name', '=', address.get('company'))]
            domain += [('company_type', '=', 'company')]
            company=env['res.partner'].sudo().search(domain, limit=1)
            address['company_id']=company.id if company else None
            address['company_name']=address.get('company', '')
        return vals


