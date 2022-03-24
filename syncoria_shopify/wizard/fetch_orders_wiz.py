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
                    return partner_id[0]

                
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

    def shopify_fetch_orders(self, kwargs=None):
        """Fetch Orders"""
        PartnerObj = self.env['res.partner'].sudo()
        OrderObj = self.env['sale.order'].sudo()
        ProductObj = self.env['product.product'].sudo()
        CarrierObj = self.env['delivery.carrier'].sudo()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        AccMove = self.env['account.move'].sudo()

        cr = self._cr
        if not kwargs:
            marketplace_instance_id = self._get_instance_id()
        else:
            marketplace_instance_id = kwargs.get("marketplace_instance_id")

        version = '2021-04'
        version = marketplace_instance_id.marketplace_api_version or '2021-04'
        url = marketplace_instance_id.marketplace_host + \
            '/admin/api/%s/orders.json' % version

        if self.date_from and not self.date_to:
            url += '?created_at_min=%s' % self.date_from.strftime(
                "%Y-%m-%dT00:00:00-04:00")
        if not self.date_from and self.date_to:
            url += '?created_at_max=%s' % self.date_to.strftime(
                "%Y-%m-%dT00:00:00-04:00")
        if self.date_from and self.date_to:
            url += '?created_at_min=%s' % self.date_from.strftime(
                "%Y-%m-%dT00:00:00-04:00")
            url += '&created_at_max=%s' % self.date_to.strftime(
                "%Y-%m-%dT00:00:00-04:00")

        # Request Parameters
        type_req = 'GET'
        headers = {
            'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password}
        order_list = self.env['marketplace.connector'].shopify_api_call(headers=headers,
                                                                        url=url,
                                                                        type=type_req)

        if url and order_list:
            _logger.info("\nurl >>>>>>>>>>>>>>>>>>>>>>" + str(url) +
                         "\nOrder #:--->" + str(len(order_list.get('orders'))))

        try:
            sp_orders = order_list['orders']
            cr.execute("select shopify_id from sale_order "
                       "where shopify_id is not null")
            orders = cr.fetchall()
            order_ids = [i[0] for i in orders] if orders else []

            cr.execute("select shopify_id from res_partner "
                       "where shopify_id is not null")
            partners = cr.fetchall()
            partner_ids = [i[0] for i in partners] if partners else []

            # need to fetch the complete required fields list
            # and their values
            cr.execute("select id from ir_model "
                       "where model='sale.order'")
            order_model = cr.fetchone()
            if not order_model:
                return

            cr.execute("select name from ir_model_fields "
                       "where model_id=%s and required=True "
                       " and store=True",
                       (order_model[0],))
            res = cr.fetchall()
            fields_list = [i[0] for i in res if res] or []
            order_vals = OrderObj.default_get(fields_list)

            cr.execute("select id from ir_model "
                       "where model='res.partner'")
            partner_model = cr.fetchone()

            if not partner_model:
                return
            cr.execute("select name from ir_model_fields "
                       "where model_id=%s and required=True"
                       " and store=True",
                       (partner_model[0],))
            res = cr.fetchall()
            fields_list = [i[0] for i in res if res] or []
            partner_vals = PartnerObj.default_get(fields_list)

            for i in sp_orders:
                if str(i['id']) not in order_ids and i['confirmed'] == True:
                    # Process Only Shopify Confirmed Orders
                    # check the customer associated with the order, if the customer is new,
                    # then create a new customer, otherwise select existing record
                    customer_id = self.shopify_find_customer_id(
                        i,
                        partner_ids,
                        partner_vals,
                        main=False)
                    # Values from configurations
                    print("customer_id===>>>," + str(customer_id))
                    product_missing = False
                    if marketplace_instance_id:
                        # Options
                        order_vals['warehouse_id'] = marketplace_instance_id.warehouse_id.id if marketplace_instance_id.warehouse_id else None
                        order_vals['company_id'] = marketplace_instance_id.company_id.id if marketplace_instance_id.company_id else None
                        order_vals['user_id'] = marketplace_instance_id.user_id.id if marketplace_instance_id.user_id else None
                        order_vals['fiscal_position_id'] = marketplace_instance_id.fiscal_position_id.id or None
                        order_vals['pricelist_id'] = marketplace_instance_id.pricelist_id.id if marketplace_instance_id.pricelist_id else None
                        order_vals['payment_term_id'] = marketplace_instance_id.payment_term_id.id if marketplace_instance_id.payment_term_id else None
                        order_vals['team_id'] = marketplace_instance_id.sales_team_id.id if marketplace_instance_id.sales_team_id else None

                    # order_vals['marketplace'] = True
                    order_vals['marketplace_type'] = 'shopify'
                    order_vals['shopify_instance_id'] = marketplace_instance_id.id
                    order_vals['shopify_id'] = str(i['id'])
                    order_vals['partner_id'] = customer_id
                    order_vals['shopify_status'] = i.get('confirmed')
                    order_vals['shopify_order'] = i.get('name')
                    order_vals['shopify_financial_status'] = i.get(
                        'financial_status')
                    order_vals['shopify_fulfillment_status'] = i.get(
                        'fulfillment_status')
                    order_vals['date_order'] = i.get('created_at')
                    if i.get('created_at'):
                        order_vals['date_order'] = i.get('created_at').split(
                            "T")[0] + " " + i.get('created_at').split("T")[1].split("+")[0].split('-')[0]

                    # Ordervals based on marketplace configuration
                    # Tax Search
                    for tax in i['tax_lines']:
                        search_domain = [('name', 'like', tax['title']),
                                        ('amount', '=', tax['rate'] * 100),
                                        ('type_tax_use', '=', 'sale'),
                                        ('marketplace_type', '=', 'shopify'),
                                        ]
                        Tax = self.env['account.tax']
                        tax_ob = Tax.search(search_domain, limit=1)
                        if not tax_ob:
                            Tax.sudo().create({
                                'name': tax['title'],
                                'amount': tax['rate'] * 100,
                                'type_tax_use': 'sale',
                                'marketplace_type': 'shopify',
                                'shopify': True
                            })

                    order_line = []
                    prod_rec = []

                    for line in i['line_items']:
                        product_tax_per = 0
                        product_tax_name = ''
                        if line.get('variant_id'):
                            prod_dom = ['|',
                                        ('shopify_id', '=', str(
                                            line['variant_id'])),
                                        ('default_code', '=',
                                         str(line['sku'])),
                                        ]
                            prod_rec = self.env['product.product'].sudo().search(
                                prod_dom, limit=1)
                        else:
                            prod_dom = ['|',
                                        ('shopify_id', '=', str(
                                            line['product_id'])),
                                        ('default_code', '=',
                                         str(line['sku'])),
                                        ]
                            prod_rec = self.env['product.product'].sudo().search(
                                prod_dom, limit=1)
                        if not prod_rec and marketplace_instance_id.auto_create_product:
                            _logger.info("# Need to create a new product")
                            sp_product_list = self.env['products.fetch.wizard'].shopify_fetch_products_to_odoo({
                                'product_id': line.get('product_id'),
                                'marketplace_instance_id': marketplace_instance_id,
                                'fetch_o_product': 'true',
                            })
                            prod_rec = self.env['product.product'].sudo().search(
                                prod_dom, limit=1)
                            if not prod_rec:
                                new_domain = [
                                    '|', ('active', '=', True), ('active', '=', False), ('shopify_id', '=', line['product_id'])]
                                prod_tmpl = self.env['product.template'].sudo().search(
                                    new_domain, limit=1)

                                if prod_tmpl:
                                    if 'product.template' in str(prod_tmpl):
                                        new_domain_new = [
                                            ('product_tmpl_id', '=', prod_tmpl.id)]
                                        prod_rec = self.env['product.product'].sudo().search(
                                            new_domain_new, limit=1)
                                        if not prod_rec:
                                            """Create a new Product"""
                                            variants = sp_product_list[0]['variants'][0]
                                            categ_id = None
                                            if sp_product_list[0]['product_type']:
                                                categ_id = self.env['product.category'].sudo().search(
                                                    [('name', '=', sp_product_list[0]['product_type'])], limit=1)
                                            uom_id = self.env['uom.uom'].sudo().search([
                                                ('name', '=', variants['weight_unit'])], limit=1)
                                            prod_vals = {
                                                'categ_id': prod_tmpl.categ_id.id,
                                                'name': sp_product_list[0]['body_html'],
                                                'product_tmpl_id': prod_tmpl.id,
                                                # 'sale_line_warn' : '',
                                                # 'tracking' : True,
                                                'type': 'product',
                                                'uom_id': uom_id.id,
                                                'uom_name': uom_id.name,
                                                'uom_po_id': uom_id.id,
                                                'marketplace_type': 'shopify',
                                                'shopify_id': variants['id'],
                                                'weight': variants['weight'],
                                                'default_code': variants['sku']
                                            }
                                            VariantObj = self.env['product.product']
                                            if not VariantObj.sudo().search([('shopify_id', '=', str(variants['id']))]):
                                                prod_rec = self.env['product.product'].sudo().create(
                                                    prod_vals)

                        product_missing == True if not prod_rec else product_missing
                        temp = {}
                        product_tax = []
                        product_tax = self._shopify_get_taxnames(
                            line['tax_lines'])
                        _logger.info("prod_rec===>>>>>" + str(prod_rec))
                        if line and line.get('quantity') > 0:
                            #####################################################################################
                            #TO DO: Compute Price from Pricelist
                            price_unit =  line.get('price_set', {}).get('shop_money', {}).get('amount')
                            pricelist_currency = marketplace_instance_id.pricelist_id.currency_id.name
                            shop_currency_code = line.get('price_set', {}).get('shop_money',{}).get('currency_code')
                            pre_currency_code = line.get('price_set', {}).get('presentment_money',{}).get('currency_code')
                            if pricelist_currency and shop_currency_code:
                                _logger.info("\npricelist_currency-{}\nshop_currency_code-{}\npre_currency_code-{}".format(pricelist_currency, shop_currency_code, pre_currency_code))
                                if pricelist_currency == shop_currency_code:
                                    _logger.info("Shop and Pricelist Currency Matches")
                                else:
                                    _logger.info("Shop and Pricelist Currency Not Matching")
                                    price_unit = self.compute_price_unit(prod_rec, price_unit)
                            
                            
                            _logger.info("price_unit-{}".format(price_unit))
                            #####################################################################################
                            temp = {
                                'product_id': prod_rec.id,
                                'product_uom_qty': line['quantity'],
                                'price_unit': price_unit,
                                'tax_id': [(6, 0, product_tax)],
                                'name': str(prod_rec.name),
                            }

                            if marketplace_instance_id.user_id:
                                temp['salesman_id'] = marketplace_instance_id.user_id.id

                            temp['marketplace_type'] = 'shopify'
                            temp['shopify_id'] = line.get('id')
                            discount = 0
                            # if line.get("total_discounts") and float(line.get("total_discounts")) != 0:
                            #     discount = line.get("total_discounts")
                            #     disc_per = (float(discount)/float(line.get("price"))) * 100
                            #     ICPSudo = self.env['ir.config_parameter'].sudo()
                            #     group_dicnt = ICPSudo.get_param(
                            #         'sale.group_discount_per_so_line')
                            #     # if group_dicnt == True:
                            #     temp['discount'] = disc_per
                            if line.get("discount_allocations") and float(line.get('total_discount')) == 0:
                                for da in line.get("discount_allocations"):
                                    discount += float(da.get('amount'))
                                disc_per = (float(
                                    discount)/(float(line.get("price")) * line.get("fulfillable_quantity")) * 100)
                                ICPSudo = self.env['ir.config_parameter'].sudo(
                                )
                                group_dicnt = ICPSudo.get_param(
                                    'sale.group_discount_per_so_line')
                                # if group_dicnt == True:
                                temp['discount'] = disc_per

                            ##################################
                            ###AD LINE ITEM ID
                            ##################################
                            order_line.append((0, 0, temp))

                        order_vals['order_line'] = order_line

                    # Set Shipping Address
                    partner_shipping_id = False
                    shipping = False

                    if i.get('shipping_address'):
                        full_name = i['shipping_address'].get(
                            'first_name') or "" + ' ' + i['shipping_address'].get('last_name') or ""
                        partner_shipping_id = self.env['res.partner'].sudo().search(
                            [('name', '=', full_name), ('type', '=', 'delivery')], limit=1)
                        update_ship = ShopifyCustomer(
                            i['shipping_address'], self.env, shipping=True)._partner_vals
                        if 'child_ids' in update_ship:
                            update_ship_child_ids = partner_vals.get('child_ids')
                            del(update_ship['child_ids'])

                        customer = self.env['res.partner'].sudo().browse(
                            customer_id) if customer_id else None
                        partner_shipping_id = self._match_or_create_address(
                            customer, i.get('shipping_address'), 'delivery')

                    order_vals['order_line'] = order_line
                    order_vals = self._get_delivery_line(
                        i, order_vals, marketplace_instance_id)
                    # Other Values

                    order_vals['shopify_status'] = i.get('status', '')
                    order_vals['shopify_order_date'] = i.get('created_at').split(
                        "T")[0] + " " + i.get('created_at').split("T")[1][:8]
                    order_vals['shopify_carrier_service'] = i.get('')
                    order_vals['shopify_has_delivery'] = i.get('')
                    order_vals['shopify_browser_ip'] = i.get('browser_ip')
                    order_vals['shopify_buyer_accepts_marketing'] = i.get(
                        'buyer_accepts_marketing')
                    order_vals['shopify_cancel_reason'] = i.get(
                        'cancel_reason')
                    order_vals['shopify_cancel_reason'] = i.get('cancelled_at')
                    order_vals['shopify_cart_token'] = i.get('cart_token')
                    order_vals['shopify_checkout_token'] = i.get(
                        'checkout_token')

                    currency = self.env['res.currency'].search(
                        [('name', '=', i.get('currency'))])
                    if currency:
                        order_vals['shopify_currency'] = currency.id
                    order_vals['shopify_financial_status'] = i.get(
                        'financial_status')
                    order_vals['shopify_fulfillment_status'] = i.get(
                        'fulfillment_status')

                    tags = i.get('tags').split(",")
                    try:
                        tag_ids = []
                        for tag in tags:
                            tag_id = self.env['crm.tag'].search(
                                [('name', '=', tag)])
                            if not tag_id and tag != "":
                                tag_id=self.env['crm.tag'].create({"name":tag,"color":1})
                            if tag_id:
                                tag_ids.append((4,tag_id.id))
                        order_vals['tag_ids'] = tag_ids
                    except Exception as e:
                        _logger.warning(e)

                    if 'message_follower_ids' in order_vals:
                        order_vals.pop('message_follower_ids')
                    order_vals['name'] = self.env['ir.sequence'].next_by_code(
                        'sale.order')

                    # Set Billing Address
                    partner_invoice_id = False
                    PartnerObj = self.env['res.partner'].sudo()
                    shipping = False
                    if i.get('billing_address'):
                        full_name = i.get('billing_address').get(
                            'first_name') or "" + ' ' + i.get('billing_address').get('last_name') or ""
                        partner_invoice_id = PartnerObj.search(
                            [('name', '=', full_name), ('type', '=', 'invoice')], limit=1)
                        update_bill = ShopifyCustomer(
                            i.get('billing_address'), self.env, shipping=True)._partner_vals
                        if 'child_ids' in update_bill:
                            update_bill_child_ids = partner_vals.get('child_ids')
                            del(update_bill['child_ids'])


                        customer = self.env['res.partner'].sudo().browse(
                            customer_id) if customer_id else None
                        partner_invoice_id = self._match_or_create_address(
                            customer, i.get('billing_address'), 'invoice')

                    pp = PartnerObj.search([('id', '=', customer_id)])
                    order_vals['partner_shipping_id'] = partner_shipping_id.id if partner_shipping_id != False else pp.id
                    order_vals['partner_invoice_id'] = partner_invoice_id.id if partner_invoice_id != False else pp.id

                    if not order_vals['partner_invoice_id']:
                        order_vals['partner_invoice_id'] = order_vals['partner_id']
                    if not order_vals['partner_shipping_id']:
                        order_vals['partner_shipping_id'] = order_vals['partner_id']

                    order_vals['pricelist_id'] = marketplace_instance_id.pricelist_id.id

                    if marketplace_instance_id.sales_team_id:
                        order_vals['team_id'] = marketplace_instance_id.sales_team_id.id
                    if marketplace_instance_id.user_id:
                        order_vals['user_id'] = marketplace_instance_id.user_id.id
                    if marketplace_instance_id.payment_term_id:
                        order_vals['payment_term_id'] = marketplace_instance_id.payment_term_id.id

                    # order_vals = self.process_discount_codes(i, order_vals)
                    pprint.pformat(order_vals)
                    order_id = False

                    if order_vals.get('order_line'):
                        _logger.warning("Order Creation Failed for Shopify Order Id: %s" % (
                            i['id'])) if product_missing else None

                        for line in order_vals['order_line']:
                            if not line[2].get('analytic_tag_ids'):
                                line[2]['analytic_tag_ids'] = [[6, False, []]]
                            if not line[2].get('product_id'):
                                product_missing = True

                        print("Product Missing", product_missing)
                        if not order_vals['partner_id']:
                            _logger.info("Unable to Create Order %s. Reason: Partner ID Missing" % (
                                order_vals['shopify_id']))
                        if not product_missing and order_vals['partner_id']:
                            order_id = OrderObj.create(order_vals)
                            _logger.info("Order Created: %s" % (order_id))

                            if i.get('confirmed'):
                                order_id.action_confirm()

                            try:
                                if order_id and order_id.state in ['sale', 'done'] and marketplace_instance_id.auto_create_invoice == True:
                                    inv = self._create_invoice_shopify(
                                        order_id, i)
                                    msg = "Invoice created with Order id: %s, Invoice Name: %s" % (
                                        order_id.name, inv.name)
                                    _logger.info(msg) if msg else None
                                else:
                                    _logger.info(
                                        "Unable to create Invoice for order id: %s" % (order_id))
                            except Exception as e:
                                _logger.warning(
                                    "Error for order id: %s- %s" % (order_id, e.args))

                else:
                    current_order_id = OrderObj.search(
                        [('shopify_id', '=', i['id'])], order='id desc', limit=1)
                    current_order_id.write({"shopify_instance_id": marketplace_instance_id.id})

                    tags = i.get('tags').split(",")
                    try:
                        tag_ids = []
                        for tag in tags:
                            tag_id = self.env['crm.tag'].search(
                                [('name', '=', tag)],limit=1)
                            if not tag_id and tag != "":
                                tag_id = self.env['crm.tag'].create({"name": tag, "color": 1})
                                # current_order_id.write({"tag_ids":[(0,0, {"name": tag, "color": 1}))
                            if tag_id:
                                tag_ids.append(tag_id.id)
                        current_order_id.tag_ids= tag_ids
                    except Exception as e:
                        _logger.warning(e)

                    if i['confirmed'] and current_order_id.state == 'draft':
                        current_order_id.action_confirm()

                    if i['confirmed'] != current_order_id.shopify_status:
                        current_order_id.shopify_status = i['confirmed']

                    if marketplace_instance_id.auto_create_invoice == True:
                        print("current_order_id===>>>" +
                              str(current_order_id.name))

                        move_id = AccMove.search(
                            [('invoice_origin', '=', current_order_id.name)], limit=1)
                        print("move_id===>>>" + str(move_id))
                        print("move_id.invoice_origin===>>>" +
                              str(move_id.invoice_origin))

                        if current_order_id and current_order_id.state in ['sale', 'done']:
                            try:
                                if not move_id:
                                    move_id = self._create_invoice_shopify(
                                        current_order_id, i)
                                    msg = "Invoice created with Order id: %s, Invoice Name: %s" % (
                                        current_order_id.name, move_id.name)
                                    _logger.info(msg) if msg else None
                                if move_id and move_id.state == 'draft' and i.get('financial_status') in ['authorized', 'paid']:
                                    move_id.action_post()

                                payments = self._shopify_process_payments(
                                    move_id, i)
                                _logger.info("payments" + str(payments))
                            except Exception as e:
                                _logger.warning(
                                    "Error for order id: %s- %s" % (current_order_id, e.args))

                        else:
                            _logger.info(
                                "Unable to create Invoice for order id: %s" % (current_order_id))

            # self.update_sync_history({
            #     'last_product_sync' : '',
            #     'last_product_sync_id' : sp_product_list[-1].get('id') if len(sp_product_list) > 0 else '',
            #     'product_sync_no': update_products_no,
            # })

        except Exception as e:
            _logger.info("Exception occured %s", e)
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

    def _create_invoice_shopify(self, order_id, sp_order):
        # ------------------------------------------------------------
        # values = {
        #     'advance_payment_method': 'delivered',
        #     'deduct_down_payments': True,
        #     'product_id': False,
        #     'currency_id': order_id.currency_id.id,
        #     'fixed_amount': 0,
        #     'amount': 0,
        #     'deposit_account_id': False,
        #     'deposit_taxes_id': [[6, False, []]],
        # }
        # sale_pay = self.env['sale.advance.payment.inv'].sudo()
        # sale_pay_id = sale_pay.create(values)

        # print("sale_pay_id ===>>>", sale_pay_id)
        # move_id = sale_pay_id.create_invoices()
        # print("move_id ===>>>", move_id)

        # wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=order_id.ids, open_invoices=True).create({})
        # move_id = wiz.create_invoices()
        # print("move_id ===>>>", move_id)
        # ------------------------------------------------------------
        move_id = order_id._create_invoices()
        move_id.update({'marketplace_type': 'shopify', })
        # payments = self._shopify_process_payments(move_id, sp_order)
        return move_id

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

    def _shopify_process_payments(self, move_id, sp_order):
        payments = False
        # ---------------------------------------------------------------
        # action_data = sheet.action_register_payment()
        # wizard =  Form(self.env['account.payment.register'].with_context(action_data['context'])).save()
        # wizard.action_create_payments()
        # mkplc_id = self._get_instance_id()
        # domain = [('code','=','manual'),('payment_type','=','inbound')]
        # payment_method_id = self.env['account.payment.method'].sudo().search(domain, limit=1)
        # reg_vals = {
        #     'amount': move_id.amount_total,
        #     'available_payment_method_ids': False,
        #     'can_edit_wizard': True,
        #     'can_group_payments': False,
        #     'communication': move_id.name,
        #     # 'company_currency_id': move_id.name,
        #     'company_id':move_id.company_id.id,
        #     'country_code':move_id.company_id.country_id.code,
        #     'currency_id':move_id.currency_id.id,
        #     'group_payment':False,
        #     'journal_id':mkplc_id.marketplace_payment_journal_id.id,
        #     'line_ids':False,
        #     'partner_bank_id':False,
        #     # 'partner_id':move_id.partner_id.id,
        #     'payment_method_id':payment_method_id.id,
        #     'payment_difference_handling':'open',
        #     # 'writeoff_account_id':False,
        #     'writeoff_label':'Write-Off',
        #     'partner_type':'customer',
        #     'payment_date':fields.Datetime.now(),
        #     'payment_type':'inbound',
        #     'source_amount':move_id.amount_total,
        #     'source_currency_id':move_id.currency_id.id,
        # }

        # pay_reg_id = self.env['account.payment.register'].with_context({
        #     'active_model': 'account.move',
        #     'active_ids': move_id.ids,
        # }).create(reg_vals)

        # print("pay_reg_id===>>>" + str(pay_reg_id))
        # pay_reg_id.action_create_payments()
        # print("pay_reg_id===>>>" + str(pay_reg_id))

        # ---------------------------------------------------------------
        # ----------------------------------------------------------------
        mkplc_id = self._get_instance_id()
        AccPay = self.env['account.payment'].sudo()
        print("move_id.payment_id===>>>" + str(move_id.payment_id))
        payments = {}
        if sp_order.get('payment_details') and move_id.amount_residual > 0:
            payment_vals_list = self._shopify_payment_vals(move_id, sp_order)
            _logger.info("" + pprint.pformat(payment_vals_list))
            pay_domain = [('ref', '=', move_id.name)]
            pay_domain += [('amount', '=', move_id.amount_residual)]
            payment = AccPay.search(pay_domain, limit=1)
            if not payment:
                payment = AccPay.create(payment_vals_list)
                _logger.info("Payment Created- %s" % (payment))

            if sp_order.get('financial_status') in ['authorized', 'paid']:
                if not payment.line_ids:
                    if payment.payment_type == 'inbound':
                        payment.write({
                            'line_ids': [(0, 0, {
                                'name': 'Customer Payment %s %s-%s' % (payment.amount, payment.currency_id.symbol, payment.date),
                                'account_id': mkplc_id.debit_account_id.id,
                                'debit': payment.amount,
                                'credit': 0,
                                'quantity': 1,
                                'date_maturity': payment.date,
                                'move_id': payment.move_id.id,
                            }),

                            (0, 0, {
                                'name': 'Customer Payment %s %s-%s' % (payment.amount, payment.currency_id.symbol, payment.date),
                                'account_id': mkplc_id.credit_account_id.id,
                                'debit': 0,
                                'credit': payment.amount,
                                'quantity': 1,
                                'date_maturity': payment.date,
                                'move_id': payment.move_id.id,
                            })

                            ]
                        })
                payment.action_post() if payment.state == 'draft' else None
                # Error for order id: sale.order(34,)- ('You need to add a line before posting.',)
                if payment.state == 'posted':
                    move_id.sudo().write({
                        'payment_id': payment.id,
                        'payment_state': 'paid',
                    })
                    payment.write({'is_reconciled': True})

        print("move_id.payment_id===>>>" + str(move_id.payment_id))
        print("move_id.payment_id.is_reconciled===>>>" +
              str(move_id.payment_id.is_reconciled))
        if move_id.payment_id:
            if move_id.payment_id.amount == move_id.amount_total and move_id.payment_id.state == 'posted':
                if move_id.payment_state != 'paid':
                    move_id.write({
                        'payment_state': 'paid',
                        'amount_residual': 0,
                        'payment_reference':  move_id.payment_id.name
                    })
                move_id.payment_id.sudo().write({
                    'is_reconciled': True,
                    # 'move_id':move_id.id
                })  # Please define a payment method on your payment.

        if sp_order.get('refunds'):
            """Create a Invoice Credit Note"""
            move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=move_id.ids).create({
                'date': fields.Datetime.now(),
                'reason': 'no reason',
                'refund_method': 'refund',
            })
            reversal = move_reversal.reverse_moves()
            reverse_move = self.env['account.move'].browse(reversal['res_id'])
            _logger.info("Reversal Move--->", reverse_move)

            for refund in sp_order.get('refunds'):
                for refund_trx in refund.get('transactions'):
                    """Create Payment Refunds"""
                    refund_tx = self._shopify_refund_vals(refund_trx)
                    refunds_vals_list = self._shopify_payment_vals(
                        reverse_move, refund_trx)
                    refund_trxs = self.env['account.payment'].create(
                        payment_vals_list)
        return payments

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
        # vals.update({
        #     'line_ids': line_ids
        # })
        # vals.update({
        #     'move_type': 'out_invoice',
        #     # 'payment_reference': 'inbound',
        #     # 'payment_transaction_id': 'inbound',
        # })
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

    # def create_new_product(self, product, prod_rec, prod_tmpl, marketplace_instance_id):
    #     if len(prod_rec) == 0 and len(prod_tmpl) > 0:
    #         print("pro_vals")
    #         child = product['variants'][0]
    #         child_file = False
    #         options = product.get('options')
    #         var = self.get_variant_combs(child)
    #         variant, variant_ids = var[0], var[1]
    #         product_template_attribute_value_ids = self.check_for_new_attrs(prod_tmpl, options)
    #         pro_vals = {
    #             'product_tmpl_id': prod_tmpl.id,
    #             'product_template_attribute_value_ids': product_template_attribute_value_ids,
    #             'list_price': child.get('price') or 0,
    #             'marketplace_type': 'shopify',
    #             'active': True,
    #             'shopify_id': str(child['id']),
    #             'default_code': child['sku'],
    #             'barcode': child['barcode'] if child['barcode'] != ''  else False,
    #             'shopify_type': 'simple',
    #             'image_1920': self.shopify_image_processing(child_file) if marketplace_instance_id.sync_product_image ==  True else False,
    #             'combination_indices': variant_ids,
    #             'shopify_com': variant_ids,
    #             'weight': child['weight'],
    #             'qty_available': child['inventory_quantity'],
    #             'compare_at_price': child['compare_at_price'],
    #             'fulfillment_service': child['fulfillment_service'],
    #             'inventory_management': child['inventory_management'],
    #             'inventory_policy': child['inventory_policy'],
    #             'requires_shipping': child['requires_shipping'],
    #             'taxable': child['taxable'],
    #         }
    #         print("\npro_vals:\n",str(pro_vals))
    #         prod_id = self.env['product.product'].sudo().create(pro_vals)
    #         print("\prod_id:\n",str(prod_id))


    def _match_or_create_address(self, partner, checkout, contact_type):
        Partner = self.env['res.partner']
        street = checkout.get('address1')
        street2 = checkout.get('address2')
        azip = checkout.get('zip')
        if partner:
            delivery = partner.child_ids.filtered(
                lambda c: c.street == street or c.street2 == street2 or c.zip == azip)

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
                        res_partner.sudo().create(add_vals)

        return vals

    

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
                SpTaxExempt=self.env['shopify.tax.exempt']
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
            if default_address.get('company'):
                company=env['res.partner'].sudo().search(
                    [('name', '=', default_address.get('company'))], limit=1)
                self._partner_vals['company_id']=company.id if company else None
                self._partner_vals['company_name']=default_address.get(
                    'company') or ""

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
