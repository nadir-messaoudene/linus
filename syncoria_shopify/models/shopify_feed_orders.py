# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import json
import requests
import base64
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

class ShopifyFeedOrders(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'shopify.feed.orders'
    _description = 'Shopify Feed Orders'

    _rec_name = 'name'
    _order = 'name DESC'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.feed.orders'))
    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    shopify_id = fields.Char(string='Shopify Id', readonly=1)
    order_data = fields.Text(readonly=1)
    state = fields.Selection(
        string='State',
        tracking=True,
        selection=[('draft', 'Draft'), 
                    ('queue', 'Queue'),
                   ('processed', 'Processed'), 
                   ('failed', 'Failed')]
        
    )
    order_wiz_id = fields.Many2one(
        string='Order Wiz',
        comodel_name='feed.orders.fetch.wizard',
        ondelete='restrict',
    )
    
    shopify_webhook_call = fields.Boolean(string='Webhook Call', readonly=1)
    shopify_app_id = fields.Char(string='App Id', readonly=1)
    shopify_confirmed = fields.Char(string='Confirmed', readonly=1)
    shopify_contact_email = fields.Char(string='Contact Email', readonly=1)
    shopify_currency = fields.Char(string='Currency', readonly=1)
    shopify_customer_name = fields.Char(string='Customer Name', readonly=1)
    shopify_customer_id = fields.Char(string='Customer ID', readonly=1)
    shopify_gateway = fields.Char(string='Gateway', readonly=1)
    shopify_order_number = fields.Char(string='Order Number', readonly=1)
    shopify_financial_status = fields.Char(string='Financial Status', readonly=1)
    shopify_fulfillment_status = fields.Char(string='Fulfillment Status', readonly=1)
    shopify_line_items = fields.Char(string='Line Items', readonly=1)
    shopify_user_id = fields.Char(string='User ID', readonly=1)
    sale_id = fields.Many2one(
        string='Odoo Order',
        comodel_name='sale.order',
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


    def compute_price_unit(self, product_id, price_unit):
        item_price = price_unit
        marketplace_instance_id = self._get_instance_id()
        pricelist_id = marketplace_instance_id.pricelist_id
        pricelist_price = marketplace_instance_id.compute_pricelist_price
        if pricelist_price and pricelist_id and 'product.product' in str(product_id):
            item_line = marketplace_instance_id.pricelist_id.item_ids.filtered(
                lambda l: l.product_tmpl_id.id == product_id.product_tmpl_id.id)
            if not item_line:
                _logger.warning("No Item Line found for {}".format(product_id))
            item_price = item_line.fixed_price if item_line else item_price
        if pricelist_price and pricelist_id and 'product.template' in str(product_id):
            item_line = marketplace_instance_id.pricelist_id.item_ids.filtered(
                lambda l: l.product_tmpl_id.id == product_id.id)
            if not item_line:
                _logger.warning("No Item Line found for {}".format(product_id))
            item_price = item_line.fixed_price if item_line else item_price
        return item_price


    def shopify_customer(self, values, env, shipping=False):
        customer={}
        customer['name']=(values.get(
            'first_name') or "") + " " + (values.get('last_name') or "")
        customer['display_name']=customer['name']
        customer['phone']=values.get('phone') or ""
        customer['email']=values.get('email') or ""
        customer['shopify_id']=values.get('id') or ""
        customer['marketplace_type']='shopify'
        customer['shopify_instance_id']=self.instance_id.id
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
            if default_address.get('company'):
                customer['shopify_company_name']=default_address.get('company')

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

    def get_partner_invoice_id(self, sp_order_dict, partner_id, no_name=False):
        res_partner = self.env['res.partner'].sudo()
        partner_invoice_id = partner_id
        if sp_order_dict.get('billing_address'):
            billing_address = sp_order_dict.get('billing_address', {})

            partner_invoice_id = partner_id.child_ids.filtered(lambda l:l.type == 'invoice' and l.street.lower() == billing_address.get('address1', '').lower() and l.zip.lower() == billing_address.get('zip', '').lower() and l.phone == billing_address.get('phone', ''))
            if partner_invoice_id:
                country_domain = []
                if billing_address.get('country_code'):
                    country_domain += [('code', '=', billing_address.get('country_code'))]

                elif billing_address.get('country'):
                    country_domain += [('name', '=', billing_address.get('country'))]
                # country_domain = [('name', '=', billing_address.get(
                #     'country'))] if billing_address.get('country') else []
                # country_domain += [('name', '=', billing_address.get('province'))
                #                     ] if billing_address.get('province') else country_domain
                country_id = self.env['res.country'].sudo().search(
                    country_domain, limit=1)

                state_domain = [('country_id', '=', country_id.id)
                                ] if country_id else []
                state_domain += [('name', '=', billing_address.get('province'))
                                ] if billing_address.get('province') else state_domain
                state_id = self.env['res.country.state'].sudo().search(
                    state_domain, limit=1)
                if not no_name:
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
                else:
                    partner_invoice_id = self.env['res.partner'].create({
                        'name': billing_address.get('name', None),
                        'street': billing_address.get('address1'),
                        'street2': billing_address.get('address2'),
                        'zip': billing_address.get('zip'),
                        'country_id': country_id.id,
                        'state_id': state_id.id,
                        'city': billing_address.get('city'),
                        'parent_id': partner_id.id,
                        'property_account_receivable_id': partner_id.property_account_receivable_id.id,
                        'property_account_payable_id': partner_id.property_account_payable_id.id,
                        'type': 'invoice'
                    })

            if not partner_invoice_id:
                partner_invoice_id = self._match_or_create_address(
                    partner_id, sp_order_dict.get('billing_address'), 'invoice')

            if partner_id and partner_invoice_id and not partner_invoice_id.property_account_receivable_id:
                partner_invoice_id.property_account_receivable_id = partner_id.property_account_receivable_id.id
            if partner_id and partner_invoice_id and not partner_invoice_id.property_account_payable_id:
                partner_invoice_id.property_account_payable_id = partner_id.property_account_payable_id.id

            if partner_invoice_id:
                partner_invoice_id[0]
        try:
            self._cr.commit()
        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))
        return partner_invoice_id

    def get_partner_shipping_id(self, sp_order_dict, partner_id, no_name=False):
        partner_shipping_id = partner_id
        if sp_order_dict.get('shipping_address'):
            shipping_address = sp_order_dict.get('shipping_address', {})
            partner_shipping_id = partner_id.child_ids.filtered(lambda l:l.type == 'delivery' and l.street.lower() == shipping_address.get('address1', '').lower() and l.zip.lower() == shipping_address.get('zip', '').lower() and l.phone == shipping_address.get('phone', ''))
            if partner_shipping_id:
                country_domain = []
                if shipping_address.get('country_code'):
                    country_domain += [('code', '=', shipping_address.get('country_code'))]

                elif shipping_address.get('country'):
                    country_domain += [('name', '=', shipping_address.get('country'))]
                # country_domain = [('name', '=', shipping_address.get(
                #     'country'))] if shipping_address.get('country') else []
                # country_domain += [('name', '=', shipping_address.get('province'))
                #                     ] if shipping_address.get('province') else country_domain
                country_id = self.env['res.country'].sudo().search(
                    country_domain, limit=1)

                state_domain = [('country_id', '=', country_id.id)
                                ] if country_id else []
                state_domain += [('name', '=', shipping_address.get('province'))
                                ] if shipping_address.get('province') else state_domain
                state_id = self.env['res.country.state'].sudo().search(
                    state_domain, limit=1)
                if not no_name:
                    if len(partner_shipping_id) > 1:
                        self.message_post(body='There are multiple contacts with the same delivery address.')
                        raise ValidationError('There are multiple contacts with the same delivery address.')
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
                        'type': 'delivery'
                    })
                else:
                    partner_shipping_id = self.env['res.partner'].create({
                        'name': shipping_address.get('name', None),
                        'street': shipping_address.get('address1'),
                        'street2': shipping_address.get('address2'),
                        'zip': shipping_address.get('zip'),
                        'phone': shipping_address.get('phone'),
                        'country_id': country_id.id,
                        'state_id': state_id.id,
                        'city': shipping_address.get('city'),
                        'parent_id': partner_id.id,
                        'property_account_receivable_id': partner_id.property_account_receivable_id.id,
                        'property_account_payable_id': partner_id.property_account_payable_id.id,
                        'type': 'delivery'
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
                partner_id = res_partner.search(domain, order='id asc', limit=1)

                if not partner_id:
                    domain = [('shopify_id', '=', shopify_id)]
                    partner_id = res_partner.search(domain, order='id asc', limit=1)
                    if not partner_id:
                        customer_vals = self.shopify_customer(customer, self.env, shipping=False)
                        partner_id = res_partner.create(customer_vals)

                if partner_id:
                    partner_invoice_id = self.get_partner_invoice_id(sp_order_dict, partner_id)
                    partner_shipping_id = self.get_partner_shipping_id(sp_order_dict, partner_id)

            try:
                self._cr.commit()
            except Exception as e:
                _logger.warning("Exception-{}".format(e.args))
        else:
            if self.instance_id.default_res_partner_id and sp_order_dict.get('tags') == 'Maisonette':
                partner_id = self.instance_id.default_res_partner_id
                partner_invoice_id = self.get_partner_invoice_id(sp_order_dict, partner_id, no_name=True)
                partner_shipping_id = self.get_partner_shipping_id(sp_order_dict, partner_id, no_name=True)
        return partner_id, partner_invoice_id, partner_shipping_id


    def process_feed_orders(self):
        for record in self:
            record.process_feed_order()

            
    def process_feed_order(self):
        """Convert Shopify Feed Order to Odoo Order"""
        msg_body = ''
        error_msg_body = ''

        
        PartnerObj = self.env['res.partner'].sudo()
        OrderObj = self.env['sale.order'].sudo()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        all_shopify_orders = self.env['sale.order'].sudo()
        try:
            for rec in self:
                log_msg = """Shopify Process Feed Order started for {}""".format(rec)
                # msg_body += '\n' + log_msg
                _logger.info(log_msg)
                
                marketplace_instance_id = self.instance_id
                i = json.loads(rec.order_data)

                order_exists = OrderObj.search(
                        [('shopify_id', '=', i['id'])], order='id desc', limit=1)
                if not order_exists and i['confirmed'] == True:
                    # Process Only Shopify Confirmed Orders
                    # check the customer associated with the order, if the customer is new,
                    # then create a new customer, otherwise select existing record
                    msg_body += "\nShopify Order ID: {}, Customer Name: {}".format(i.get('id'), i.get('name'))
                    partner_id, partner_invoice_id, partner_shipping_id = self.get_customer_id(sp_order_dict=i)
                    customer_id = partner_id.id
                    print("partner_id ===>>>>{}".format(partner_id))
                    print("partner_invoice_id ===>>>>{}".format(partner_invoice_id))
                    print("partner_shipping_id ===>>>>{}".format(partner_shipping_id))

                    product_missing = False
                    order_vals = self.get_sale_order_vals(marketplace_instance_id, customer_id, i)
                    order_vals.update({
                        'partner_id': partner_id.id,
                        'partner_invoice_id': partner_invoice_id.id,
                        'partner_shipping_id': partner_shipping_id.id,
                    })
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
                        # if not str(line['sku']) =='':
                        if line.get('variant_id'):
                            product_product = self.env['product.product'].sudo()
                            # prod_dom = [('shopify_instance_id','=',marketplace_instance_id.id)]
                            # if line.get("sku"):
                                # prod_dom += ['|']
                            # prod_dom += [('shopify_id', '=', str(line['variant_id']))]
                            prod_dom = [('default_code', '=', str(line['sku']))]
                            # else:
                            #     prod_dom += [('shopify_id', '=', str(line['variant_id']))]
                            prod_rec = product_product.search(prod_dom, limit=1)
                        else:
                            product_product = self.env['product.product'].sudo()
                            # prod_dom = [('shopify_instance_id','=',marketplace_instance_id.id)]
                            # if line.get("sku"):
                            #     prod_dom += ['|']
                            # prod_dom += [('shopify_id', '=', str(line['product_id']))]
                            prod_dom = [('default_code', '=', str(line['sku']))]
                            if not line['sku']:
                                prod_dom = [('default_code', '=', str(line['name']))]
                            # else:
                            #     prod_dom += [('shopify_id', '=', str(line['variant_id']))]
                            prod_rec = product_product.search(prod_dom, limit=1)
                            # prod_dom = [
                            #      ('shopify_instance_id', '=', marketplace_instance_id.id),
                            #     '|',
                            #             ('shopify_id', '=', str(
                            #                 line['product_id'])),
                            #             ('default_code', '=',
                            #              str(line['sku'])),
                            #             ]
                            # prod_rec = self.env['product.product'].sudo().search(
                            #     prod_dom, limit=1)
                        # else:
                        #     prod_rec =False
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


                        if not prod_rec:
                            prod_rec_variant_id = line.get('variant_id') or line.get('product_id') or ''
                            log_msg = """Product not found for Shopify ID-{}, Name: {}, SKU: {}""".format(prod_rec_variant_id, line.get('name'), line.get('sku'))
                            msg_body += '\n' + log_msg

                        product_missing == True if not prod_rec else product_missing
                        temp = {}
                        product_tax = []
                        product_tax = self._shopify_get_taxnames(
                            line['tax_lines'])
                        _logger.info("prod_rec===>>>>>" + str(prod_rec))
                        if line and line.get('quantity') > 0:
                            #####################################################################################
                            #TO DO: Compute Price from Pricelist
                            price_unit =  float(line.get('price_set', {}).get('shop_money', {}).get('amount'))
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
                                'tax_id': [(6, 0, product_tax)] if marketplace_instance_id.apply_tax else False,
                                'name': str(prod_rec.name),
                            }

                            if marketplace_instance_id.user_id:
                                temp['salesman_id'] = marketplace_instance_id.user_id.id

                            temp['marketplace_type'] = 'shopify'
                            temp['shopify_id'] = line.get('id')
                            discount = 0
                            if line.get("discount_allocations") and float(line.get('total_discount')) == 0:
                                for da in line.get("discount_allocations"):
                                    discount += float(da.get('amount'))
                                disc_per = (float(
                                    discount)/(float(line.get("price")) * line.get("quantity")) * 100)
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
                    shipping = False



                    order_vals['order_line'] = order_line
                    order_vals = self._get_delivery_line(i, order_vals, marketplace_instance_id)
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
                            if "B2C" in tag and marketplace_instance_id.id == 1:
                                tag_b2b = self.env['crm.tag'].sudo().search([('name', '=', 'B2C')])
                                if tag_b2b:
                                    order_vals['tag_ids'] = [(4, tag_b2b.id)]
                            tag_id = self.env['crm.tag'].search(
                                [('name', '=', tag)])
                            if not tag_id and tag != "":
                                tag_id=self.env['crm.tag'].create({"name":tag,"color":1})
                            if tag_id:
                                tag_ids.append((4,tag_id.id))
                        order_vals['shopify_tag_ids'] = tag_ids
                        if not order_vals.get('tag_ids'):
                            tag_b2c = self.env['crm.tag'].sudo().search([('name', '=', 'B2B')])
                            if tag_b2c:
                                order_vals['tag_ids'] = [(4, tag_b2c.id)]
                    except Exception as e:
                        _logger.warning(e)

                    """ COUPONS """
                    if 'discount_codes' in i:
                        coupon_ids = []
                        for coupon in i['discount_codes']:
                            coupon_name = self.env['shopify.coupon'].sudo().search([('name', '=', coupon.get('code'))])
                            if not coupon_name:
                                coupon_name = self.env['shopify.coupon'].create({"name": coupon.get('code')})
                            if coupon_name:
                                coupon_ids.append((4, coupon_name.id))
                        if coupon_ids:
                            order_vals['coupon_ids'] = coupon_ids

                    if 'message_follower_ids' in order_vals:
                        order_vals.pop('message_follower_ids')
                    order_vals['name'] = self.env['ir.sequence'].next_by_code('sale.order')

                    # Set Billing Address
                    partner_invoice_id = False
                    PartnerObj = self.env['res.partner'].sudo()
                    shipping = False
                    pp = PartnerObj.search([('id', '=', customer_id)])
                    order_vals['partner_shipping_id'] = partner_shipping_id.id if partner_shipping_id != False else pp.id
                    order_vals['partner_invoice_id'] = partner_invoice_id.id if partner_invoice_id != False else pp.id

                    if not order_vals['partner_invoice_id']:
                        order_vals['partner_invoice_id'] = order_vals['partner_id']
                    if not order_vals['partner_shipping_id']:
                        order_vals['partner_shipping_id'] = order_vals['partner_id']

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
                        if product_missing:
                            log_msg = """Product is missing for Feed Order-{}""".format(self)
                            msg_body += '\n' + log_msg
                            error_msg_body +=  '\n' + log_msg
                            log_msg = """Odoo Order cannot be created for Feed Order-{}""".format(self)
                            error_msg_body +=  '\n' + log_msg
                            _logger.info(log_msg)
                            self.write({'state':'failed'})
                            

                        if not order_vals['partner_id']:
                            log_msg = "Unable to Create Order %s. Reason: Partner ID Missing" % (
                                order_vals['shopify_id'])
                            msg_body += '\n' + log_msg
                            error_msg_body +=  '\n' + log_msg
                            _logger.info(log_msg)
                            self.write({'state':'failed'})

                            
                        if not product_missing and order_vals['partner_id']:
                            note_attributes = i.get('note_attributes')
                            customer_reference = False
                            for note_attribute in note_attributes:
                                if note_attribute.get('name') == 'ShipEarly Order ID':
                                    customer_reference = note_attribute.get('value')
                            if customer_reference:
                                order_vals['client_order_ref'] = customer_reference
                            order_id = self.env['sale.order'].sudo().create(order_vals)
                            log_msg = "Sale Order Created-{} for Feed Order-{}".format(order_id, self)
                            msg_body += '\n' + log_msg + '\n'
                            _logger.info(log_msg)

                            if order_id:
                                self.write({
                                    'state':'processed',
                                    'sale_id':order_id.id,
                                })
                                all_shopify_orders += order_id


                            if i.get('confirmed'):
                                order_id.with_context({'date_order': order_vals['date_order']}).action_confirm()
                                # order_id.action_confirm()

                            if i.get("cancel_reason")and i.get('cancelled_at'):
                                order_id.action_cancel()


                else:
                    current_order_id = OrderObj.search(
                        [('shopify_id', '=', i['id'])], order='id desc', limit=1)
                    current_order_id.write({"shopify_instance_id": marketplace_instance_id.id})
                    note_attributes = i.get('note_attributes')
                    customer_reference = False
                    for note_attribute in note_attributes:
                        if note_attribute.get('name') == 'ShipEarly Order ID':
                            customer_reference = note_attribute.get('value')
                    if customer_reference:
                        current_order_id.write({"client_order_ref": customer_reference})
                    if i.get("cancel_reason") and i.get('cancelled_at'):
                        current_order_id.action_cancel()
                    all_shopify_orders += current_order_id

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

                        if tag_ids:
                            current_order_id.shopify_tag_ids = tag_ids
                        else:
                            current_order_id.shopify_tag_ids.unlink()

                    except Exception as e:
                        _logger.warning(e)

                    log_msg = """Shopify Order exists for Feed Order {}, Sale Order-{}""".format(self, order_exists)
                    msg_body += '\n' + log_msg
                    _logger.info(log_msg)
                    self.write({'state':'processed'})

                if order_exists:
                    order_id = current_order_id
                else:
                    order_id = order_id

                if order_id.state not in ['cancel'] and i['fulfillments'] and marketplace_instance_id.auto_create_fulfilment :
                    shopify_fulfil_obj = self.env['shopify.fulfilment']
                    for fulfillment in i['fulfillments']:
                        exist_fulfilment = shopify_fulfil_obj.search([("shopify_fulfilment_id", "=", fulfillment['id']),
                                                                      ("shopify_instance_id", "=", marketplace_instance_id.id),
                                                                      ("sale_order_id","=",order_id.id)],limit=1)

                        fulfillment_vals = {
                            "name": order_id.name+'#'+str(fulfillment.get("order_id"))[:3],
                            "sale_order_id": order_id.id,
                            "shopify_instance_id": marketplace_instance_id.id,
                            "shopify_order_id": fulfillment.get("order_id"),
                            "shopify_fulfilment_id": fulfillment.get("id"),
                            "shopify_fulfilment_tracking_number": ','.join(fulfillment.get("tracking_numbers")),
                          "shopify_fulfilment_status": i.get("fulfillment_status") or fulfillment.get("line_items")[0].get("fulfillment_status"),
                          "shopify_status": fulfillment.get("status")
                        }
                        fulfillment_line_vals=[]
                        for line_item in fulfillment.get("line_items"):
                            fulfillment_line_vals +=[(0,0,{
                                "sale_order_id": order_id.id,
                                "name":order_id.name+":"+line_item.get("name"),
                                "shopify_instance_id": marketplace_instance_id.id,
                              "shopify_fulfilment_line_id": line_item.get("id"),
                             "shopify_fulfilment_product_id": line_item.get("product_id"),
                             "shopify_fulfilment_product_variant_id": line_item.get("variant_id"),
                             "shopify_fulfilment_product_title": line_item.get("title"),
                             "shopify_fulfilment_product_name": line_item.get("name"),
                             "shopify_fulfilment_service": line_item.get("fulfillment_service"),
                             "shopify_fulfilment_qty": line_item.get("quantity"),
                             "shopify_fulfilment_grams": line_item.get("grams"),
                             "shopify_fulfilment_price": line_item.get("price"),
                             "shopify_fulfilment_total_discount": line_item.get("total_discount"),
                             "shopify_fulfilment_status": line_item.get("total_discount"),
                            })]
                        fulfillment_vals["shopify_fulfilment_line"] = fulfillment_line_vals
                        if exist_fulfilment:
                            shopify_fulfil_obj.update(fulfillment_vals)
                        else:
                            shopify_fulfil_obj.create(fulfillment_vals)
                log_msg = """Shopify Process Feed Order finished for {}""".format(self)
                msg_body += '\n' + log_msg
                _logger.info(log_msg)
                rec.message_post(body=msg_body)
               
        except Exception as e:
            msg = "Exception occured in process feed order{}".format(e.args)
            _logger.warning(_(msg))


        ################################################################
        ###########Fetch the Payments and Refund for the Orders#########
        ################################################################
        for shopify_order in all_shopify_orders:
            order_feed_id = self.search([('shopify_id', '=', shopify_order.shopify_id)], limit=1)
            if order_feed_id:
                feed_data = json.loads(order_feed_id.order_data)
                shopify_order.fetch_shopify_payments()
                if feed_data.get('refunds'):
                    shopify_order.fetch_shopify_refunds()
                if feed_data.get('fulfillments'):
                    shopify_order.get_order_fullfillments()
                # if shopify_order and shopify_order.state in ['sale', 'done'] and marketplace_instance_id.auto_create_invoice == True:
                if shopify_order and shopify_order.state not in ['draft'] and marketplace_instance_id.auto_create_invoice == True:
                    shopify_order.process_shopify_invoice()
                    shopify_order.shopify_invoice_register_payments()
                    shopify_order.process_shopify_credit_note()
                    shopify_order.shopify_credit_note_register_payments()
            # if shopify_order and shopify_order.state not in ['draft'] and marketplace_instance_id.auto_create_fulfilment == True:
            #     shopify_order.process_shopify_fulfilment()
            shopify_order._cr.commit()


        return msg_body, error_msg_body
            



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
                    'tax_id': [(6, 0, ship_tax)] if marketplace_instance_id.apply_tax else False,
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
                tax_ob = Tax.sudo().create({
                    'name': tax_id['title'],
                    'amount': tax_id['rate'] * 100,
                    'type_tax_use': 'sale',
                    'marketplace_type': 'shopify',
                    'shopify': True,
                })

            tax_names.append(tax_ob.id)
        return tax_names

    def _match_or_create_address(self, partner, checkout, contact_type):
        Partner = self.env['res.partner']
        street = checkout.get('address1')
        street2 = checkout.get('address2')
        azip = checkout.get('zip')
        if partner:
            # delivery = partner.child_ids.filtered(
            #     lambda c: (c.street == street or c.street2 == street2 or c.zip == azip) and c.type == contact_type and c.phone == checkout.get('phone'))
            delivery = False
            country_domain = []
            if checkout.get('country_code'):
                country_domain += [('code', '=', checkout.get('country_code'))]

            elif checkout.get('country'):
                country_domain += [('name', '=', checkout.get('country'))]
            # country_domain = [('name', '=', checkout.get(
            #     'country'))] if checkout.get('country') else []
            # country_domain += [('name', '=', checkout.get('province'))
            #                     ] if checkout.get('province') else country_domain
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
                    'phone': checkout.get('phone'),
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

