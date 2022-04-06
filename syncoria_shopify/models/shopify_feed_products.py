# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import json
import requests
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class ShopifyFeedProducts(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'shopify.feed.products'
    _description = 'Shopify Feed Products'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.feed.products'))
    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )

    parent = fields.Boolean(default=False)
    title = fields.Char(copy=False)
    shopify_id = fields.Char(string='Shopify Id', readonly=1)
    inventory_id = fields.Char(string='Inventory Id', readonly=1)
    product_data = fields.Text(
        string='Json Data',
    )

    state = fields.Selection(
        string='state',
        tracking=True,
        selection=[('draft', 'draft'), ('queue', 'Queue'),
                   ('processed', 'Processed'), ('failed', 'Failed')]
    )

    product_id = fields.Many2one(
        string='Product Variant',
        comodel_name='product.product',
        ondelete='restrict',
    )
    product_tmpl_id = fields.Many2one(
        string='Parent Product',
        comodel_name='product.template',
        ondelete='restrict',
    )
    product_wiz_id = fields.Many2one(
        string='Product Wiz',
        comodel_name='feed.products.fetch.wizard',
        ondelete='restrict',
    )
    barcode = fields.Char(
        string='Barcode',
    )
    default_code = fields.Char(
        string='Default Code(SKU)',
    )
    
    

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        if self.product_id and self.product_tmpl_id:
            raise UserError(_("Only one can be added"))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and self.product_tmpl_id:
            raise UserError(_("Only one can be added"))

    def update_product_product(self):
        _logger.info("update_product_product")
        if self.product_id:
            self.product_id.write({
                'shopify_id' : self.shopify_id,
                'shopify_inventory_id' : self.inventory_id,
                'marketplace_type' : 'shopify',
            })

    def update_product_template(self):
        _logger.info("update_product_template")
        if self.product_tmpl_id:
            self.product_tmpl_id.write({
                'shopify_id' : self.shopify_id,
                'shopify_inventory_id' : self.inventory_id,
                'marketplace_type' : 'shopify',
            })


    #TO DO: Feed Products to Odoo Products
    def process_feed_product(self):
        """Convert Shopify Feed Product to Odoo Product"""
        for rec in self:
            config_products = json.loads(rec.product_data)

            categ_list = []
            existing_prod_ids = []
            try:
                attributes = {}
                attributes['items'] = []

                simple_products = {}
                simple_products['items'] = []

                if config_products.get('product_type') not in categ_list and config_products.get('product_type') != '':
                    categ_list.append(config_products.get('product_type'))

                try:
                    self.shopify_update_categories(categ_list)
                except Exception as e:
                    _logger.warning("Exception occured %s", e)
                    raise UserError(_("Error Occured %s") % e)

                if len(config_products.get('variants')) == 1:
                    simple_products['items'].append(config_products)

                if config_products.get('options'):
                    for option in config_products.get('options'):
                        attribute = {}
                        attribute['attribute_id'] = str(option.get('id'))
                        attribute['label'] = str(option.get('name'))
                        attribute['attribute_code'] = str(option.get('name'))
                        attribute['options'] = option.get('values')
                        attributes['items'].append(attribute)

                tmpl_vals = self.find_default_vals('product.template')
                product_type = 'configurable_product' if len(config_products.get('variants')) > 1 else 'simple_product'
                config_products = [config_products]
                self._shopify_import_products_list(config_products,
                                          existing_prod_ids,
                                          tmpl_vals,
                                          attributes,
                                          self.instance_id,
                                          product_type)
            except Exception as e:
                _logger.warning("Exception occured: %s", e)
                raise UserError(_("Error Occured %s") % e)

    def shopify_update_categories(self, categ_list):
        """Updating category list from shopify to odoo"""
        for categ in categ_list:
            if not self.env['product.category'].search([('name', '=', categ)]):
                self.env['product.category'].create({
                    'name': categ,
                    'parent_id': None,
                    'marketplace_type': 'shopify'
                })
        return


    def _shopify_import_products_list(self,
                                      config_products,
                                      existing_prod_ids,
                                      template,
                                      attributes,
                                      instance_id,
                                      product_type
                                      ):
        """
            The aim of this function is to configure all the
            configurable products with their variants
            config_products: configurable products list from shopify with their childs
            existing_prod_ids: products synced with shopify
            template: required fields with their values for product template
            attributes: complete list of attributes from shopify
        """

        VariantObj = self.env['product.product']
        cr = self._cr
        # fetching all the attributes and their values
        # dictionary of lists with attributes, values and id from shopify
        # if this attribute is not synced with odoo, we will do it now
        cr.execute("select id, name from product_attribute where "
                   " name is not null")
        all_attrib = cr.fetchall()

        odoo_attributes = {}
        for j in all_attrib:
            if j[1] and j[0]:
                odoo_attributes[j[1]] = j[0]

        attributes_list = {}
        for att in attributes['items']:
            if att['attribute_code'] in odoo_attributes:
                # existing attribute
                attributes_list[str(att['attribute_id'])] = {
                    # id of the attribute in odoo
                    'id': odoo_attributes[att['attribute_code']],
                    'code': att['attribute_code'],  # label
                    'options': {}
                }

        # update attribute values
        cr.execute("select id, name from product_attribute_value "
                   " where name is not null")
        all_attrib_vals = cr.fetchall()

        odoo_attribute_vals = {}
        for j in all_attrib_vals:
            if j[1] and j[0]:
                odoo_attribute_vals[j[1]] = j[0]

        for att in attributes['items']:
            for option in att['options']:
                if option != '' and option != None \
                        and option in odoo_attribute_vals \
                        and str(att['attribute_id']) in attributes_list:
                    value_rec = odoo_attribute_vals[option]
                    attributes_list[str(att['attribute_id'])]['options'][
                        option] = value_rec

        product_ids = self.env['product.product'].search(
            [('custom_option', '=', True)])
        # default_code_lst = []
        cust_list = product_ids.mapped('default_code')

        # now the attributes list should be a dictionary with all the attributes
        # with their id and values both in odoo and shopify+++++
        
        _logger.info("START===>>>")
        for product in config_products:
            _logger.info("product===>>>{}".format(product.get('id')))
            if str(product['id']) not in existing_prod_ids:
                try:
                    product_categ_ids = []
                    if product.get('product_type'):
                        product_categ_ids = [product.get('product_type')] or []

                    # getting odoo's category id from the shopify categ id
                    # (which is already created)
                    c_ids = []
                    if product_categ_ids:
                        cr.execute("select name from product_category "
                                   "where name in %s",
                                   (tuple(product_categ_ids),))
                        c_ids = cr.fetchall()

                    template['name'] = product['title']
                    template['shopify_id'] = str(product['id'])
                    template['shopify_instance_id'] = instance_id.id
                    #Product Type
                    #[consu] Consumable
                    #[service] Service
                    #[product] Storable
                    template['detailed_type'] = 'product'
                    template['active'] = True if product.get(
                        'status') == 'active' else False
                    template['active'] = True
                    template['sale_ok'] = True
                    template['purchase_ok'] = True
                    template['marketplace_type'] = 'shopify'
                    template['default_code'] = product.get('sku')
                    template['shopify_published_scope'] = product.get(
                        'published_scope')
                    template['shopify_tags'] = product.get('tags')
                    template['shopify_template_suffix'] = product.get(
                        'template_suffix')
                    template['shopify_variants'] = str(
                        len(product.get('variants')))

                    # -------------------------------------Invoice Policy------------------------------------------------
                    marketplace_instance_id = self.instance_id
                    if marketplace_instance_id.default_invoice_policy:
                        template['invoice_policy'] = marketplace_instance_id.default_invoice_policy
                    # if marketplace_instance_id.sync_price == True:
                    #     template['list_price'] = product.get('price') or 0
                    # ---------------------------------------------------------------------------------------------------

                    if len(product.get('variants')) > 1:
                        template['shopify_type'] = 'config'
                    else:
                        template['shopify_type'] = 'simple'
                        template['default_code'] = product.get('variants')[
                            0].get('sku')

                    template['custom_option'] = False
                    # New addition
                    template['weight'] = product.get('weight') or 0
                    if product.get('product_type'):
                        categ_id = self.env['product.category'].search([
                            ('name', '=', product.get('product_type'))
                        ], limit=1)
                        if len(categ_id) > 0:
                            template['categ_id'] = categ_id.id

                    # creating products
                    product_tmpl_id = self.env['product.template'].sudo().search(
                        [('shopify_id', '=', str(product['id'])),('shopify_instance_id','=',marketplace_instance_id.id)])
                    if product_tmpl_id:
                        pro_tmpl = self.env['product.template'].browse(
                            product_tmpl_id.id)
                        pro_tmpl.write({"shopify_instance_id":instance_id.id})
                        product_tmpl_id = [product_tmpl_id.id]

                    else:
                        template = self.shopify_process_options(product, template)
                        pro_tmpl = self.env['product.template'].sudo().create(template)
                        product_tmpl_id = [pro_tmpl.id]


                    _logger.info("\nproduct_tmpl_id-->" + str(product_tmpl_id))
                    _logger.info("\npro_tmpl-->" + str(pro_tmpl))

                    image_file = False

                    if marketplace_instance_id.sync_product_image == True:
                        try:
                            for pic in product['images']:
                                if 'src' in pic:
                                    image_file = pic.get('src')
                                    pro_tmpl.update({'image_1920': self.shopify_image_processing(image_file),
                                                    'default_code': product.get('sku')})
                        except:
                            _logger.info(
                                "unable to import image url of product sku %s", product.get('sku'))

                    if product.get('variants'):
                        # here we create template for main product and variants for
                        # the child products

                        if len(product.get('variants')) == 1:
                            pro_tmpl.write({
                                'default_code': product.get('variants')[0].get('sku'),
                                'weight': product.get('variants')[0].get('weight'),
                                'qty_available': product.get('variants')[0].get('inventory_quantity'),
                            })

                        if len(product.get('variants')) > 0:
                            # since this product has variants, we need to get the
                            # variant options associated with this product
                            # we are updating the attributes associated with this product
                            # (if it is not added to odoo already)

                            ###############################################################################
                            ###############################################################################

                            options = product.get('options')
                            for option in options:
                                option['attribute_id'] = option.get('id')

                            # attributes_list = self._shopify_update_attributes(
                            #     attributes_list,
                            #     options,
                            #     attributes['items']
                            # )

                            attrib_line = {}
                            child_file = False

                            for child in product['variants']:
                                variant_categ_ids = []
                                variant_att_vals = []

                                option_keys = ['option1', 'option2', 'option3']
                                option_names = []
                                for key, value in child.items():
                                    if key in option_keys:
                                        if child[key] != None:
                                            option_names.append(child[key])

                                #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
                                #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
                                if product.get('image'):
                                    images = product.get('image') if type(product.get('image')) == list else [product.get('image')]
                                    for image in images:
                                        if image['id'] == child['image_id']:
                                            child_file = image['src']

                                domain = [("product_tmpl_id","=",pro_tmpl.id)]
                                for option in option_names:
                                    domain += [("product_template_attribute_value_ids.name","=",option)]
                                # self.env['product.product'].search([("product_tmpl_id","=",28),("product_template_attribute_value_ids.name","=","ALLOY/SILVER"),("product_template_attribute_value_ids.name","=","700c")])
                                print("domain ====>>>>", domain)
                                product_id = self.env['product.product'].search(domain, limit=1)

                                if product_id:
                                    if child.get('weight'):
                                        if product_id.uom_id.name == child['weight']:
                                            weight = child['weight']
                                        else:
                                            "Convert"
                                            #TO DO:
                                            weight = child['weight']/2.2

                                    barcode = None
                                    if child.get('barcode'):
                                        barcodes = self.env['product.product'].search([]).mapped(
                                            'barcode') + self.env['product.template'].search([]).mapped('barcode')
                                        if child.get('barcode') not in child.get('barcode'):
                                            barcode = child.get('barcode')

                                    product_id.write({
                                        'marketplace_type': 'shopify',
                                        'shopify_instance_id': instance_id.id,

                                        'shopify_id': str(child['id']),
                                        # 'shopify_product_id': str(child['product_id']),
                                        'list_price': str(child['price']),
                                        'default_code': child['sku'],
                                        'inventory_policy': child['inventory_policy'],
                                        'compare_at_price': child['compare_at_price'],
                                        'fulfillment_service': child['fulfillment_service'],
                                        'inventory_management': child['inventory_management'],
                                        # 'shopify_taxable': child['taxable'],
                                        'barcode': barcode,
                                        'shopify_image_id' : child['image_id'],
                                        'shopify_inventory_id' : child['inventory_item_id'],
                                        #Weight
                                        # 'shopify_inventory_id' : child['inventory_quantity'],
                                        # 'old_inventory_quantity' : child['old_inventory_quantity'],
                                        # 'admin_graphql_api_id' : child['admin_graphql_api_id'],
                                        'shopify_type': 'simple',
                                        'image_1920': self.shopify_image_processing(child_file) if marketplace_instance_id.sync_product_image == True else False,
                                        'qty_available': child['inventory_quantity'],
                                        
                                        'requires_shipping': child['requires_shipping'],
                                        'taxable': child['taxable'],
                                        
                                    })
                                    ############TO DO################################################################
                                    # if marketplace_instance_id.marketplace_fetch_quantity == True:
                                    #     """Update Product Quantity in Odoo"""
                                    #     product_stock = child['inventory_quantity']
                                    #     # updating qty on hand
                                    #     UpdateQtyWiz = self.env['stock.change.product.qty']
                                    #     default_location = None
                                    #     company_user = self.env.user.company_id
                                    #     warehouse_id = marketplace_instance_id.warehouse_id
                                    #     if not warehouse_id:
                                    #         warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)],
                                    #                                                             limit=1)

                                    #     inventory_wizard = UpdateQtyWiz.create({
                                    #         'product_id': prod.id,
                                    #         'product_tmpl_id': prod.product_tmpl_id.id,
                                    #         'new_quantity': product_stock,
                                    #     })
                                    #     inventory_wizard.change_product_qty()
                                    ############TO DO################################################################
                                # else:
                                #     product = self.env['product.product']
                                #     current_product = product.search([("shopify_id", "=", str(child['id']))])
                                #     current_product.write({"shopify_instance_id": instance_id.id})
                                #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
                                #+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


                                for option in options:
                                    att_id = str(option['attribute_id'])
                                    current_att_id = attributes_list[att_id]['id']
                                    if current_att_id not in attrib_line:
                                        attrib_line[current_att_id] = []
                                    att_code = attributes_list[att_id]['code']
                                    att_options = attributes_list[att_id]['options']

                                    att_code_id = self.env['product.attribute'].sudo().search(
                                        [('name', '=', att_code)])
                                    if att_code_id:
                                        for key, value in attrib_line.items():
                                            if key in att_code_id.ids:
                                                attrib_line[key] = [
                                                    value for key, value in att_options.items()]

                                    att_values = []
                                    if att_options:
                                        for key, value in att_options.items():
                                            if key in option_names:
                                                att_values.append(
                                                    att_options[key])






                                # # attribute_id-->product.attribue
                                # for line in attrib_line:
                                #     if attrib_line[line]:
                                #         # cr.execute(
                                #         #     "insert into product_template_attribute_line "
                                #         #     "(attribute_id, product_tmpl_id, value_ids) "
                                #         #     "values(%s, %s. %s) returning id",
                                #         #     (line, product_tmpl_id[0], tuple(attrib_line[line])))
                                #         # line_id = cr.fetchone()

                                #         line_arr = [line] if type(
                                #             line) == int else line
                                #         domain = [('attribute_id', 'in', line_arr),
                                #                   ('product_tmpl_id', '=',
                                #                    product_tmpl_id[0]),
                                #                   ('value_ids', 'in', attrib_line[line])]
                                #         line_rec = self.env['product.template.attribute.line'].search(
                                #             domain)
                                #         if not line_rec:
                                #             print("product_tmpl_id")
                                #             print(product_tmpl_id)

                                #             Ptal = self.env['product.template.attribute.line'].sudo(
                                #             )
                                #             line_values = {
                                #                 'attribute_id': line,
                                #                 'product_tmpl_id': product_tmpl_id[0],
                                #                 'value_ids': [(6, 0, attrib_line[line])]
                                #             }
                                #             print("line_values")
                                #             print(line_values)
                                #             print("Error Here")
                                #             line_rec = Ptal.create(line_values)

                                # # creating variants
                                # if str(child['id']) not in existing_prod_ids:
                                #     var = self.get_variant_combs(child)
                                #     PtAv = self.env['product.template.attribute.value']
                                #     variant, variant_ids = var[0], var[1]
                                #     template_id = self.env['product.template'].search(
                                #         [('id', '=', product_tmpl_id[0]), ('active', 'in', (True, False))], limit=1)

                                #     _logger.info(
                                #         "product_tmpl_id===>>>" + str(product_tmpl_id))
                                #     _logger.info(
                                #         "template_id==>" + str(template_id))
                                #     if product_tmpl_id and not template_id:
                                #         _logger.warning(
                                #             """Need to create Template if missing""")

                                #     product_template_attribute_value_ids = self.check_for_new_attrs(
                                #         template_id, options)

                                #     # variant_att_vals = PtAv.search([('name', 'in', option_names)])
                                #     domain = [
                                #         ('combination_indices',
                                #          'in', variant_ids.ids),
                                #         ('product_tmpl_id', '=',
                                #          product_tmpl_id[0]),
                                #     ]

                                #     exit_prod_id = VariantObj.sudo().search(domain)
                                #     _logger.info("exit_prod_id===>%s" %
                                #                  (str(exit_prod_id)))

                                #     # Search the Product with Attribute Values
                                #     print(option_names)
                                #     pro_var = VariantObj.sudo().search([
                                #         ('product_tmpl_id', '=',
                                #          product_tmpl_id[0]),
                                #         # ('marketplace_type','=', 'shopify'),
                                #     ])

                                #     pro_var_flag = False
                                #     if pro_var:
                                #         print("pro_var")
                                #         for prod in pro_var:
                                #             print(
                                #                 prod.product_template_attribute_value_ids)
                                #             if len(prod.product_template_attribute_value_ids) > 0:
                                #                 if prod.product_template_attribute_value_ids[0].name == child.get('title'):
                                #                     # Update this product
                                #                     pro_var_flag = True
                                #                     weight = child['weight']
                                #                     if child['weight_unit'] != 'lb':
                                #                         weight = child['weight']/2.2
                                #                     barcode = None
                                #                     if child.get('barcode'):
                                #                         barcodes = self.env['product.product'].search([]).mapped(
                                #                             'barcode') + self.env['product.template'].search([]).mapped('barcode')
                                #                         if child.get('barcode') not in child.get('barcode'):
                                #                             barcode = child.get(
                                #                                 'barcode')

                                #                     prod.write({
                                #                         # 'list_price': child.get('price') or 0,
                                #                         'marketplace_type': 'shopify',
                                #                         'shopify_id': str(child['id']),
                                #                         'shopify_instance_id': instance_id.id,
                                #                         'default_code': child['sku'],
                                #                         'barcode': barcode,
                                #                         'shopify_type': 'simple',
                                #                         'image_1920': self.shopify_image_processing(child_file) if marketplace_instance_id.sync_product_image == True else False,
                                #                         'combination_indices': variant_ids,
                                #                         'shopify_com': variant_ids,
                                #                         'weight': weight,
                                #                         'qty_available': child['inventory_quantity'],
                                #                         'compare_at_price': child['compare_at_price'],
                                #                         'fulfillment_service': child['fulfillment_service'],
                                #                         'inventory_management': child['inventory_management'],
                                #                         'inventory_policy': child['inventory_policy'],
                                #                         'requires_shipping': child['requires_shipping'],
                                #                         'taxable': child['taxable'],
                                #                     })

                                #                     if marketplace_instance_id.marketplace_fetch_quantity == True:
                                #                         """Update Product Quantity in Odoo"""
                                #                         product_stock = child['inventory_quantity']
                                #                         # updating qty on hand
                                #                         UpdateQtyWiz = self.env['stock.change.product.qty']
                                #                         default_location = None
                                #                         company_user = self.env.user.company_id
                                #                         warehouse_id = marketplace_instance_id.warehouse_id
                                #                         if not warehouse_id:
                                #                             warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)],
                                #                                                                               limit=1)

                                #                         inventory_wizard = UpdateQtyWiz.create({
                                #                             'product_id': prod.id,
                                #                             'product_tmpl_id': prod.product_tmpl_id.id,
                                #                             'new_quantity': product_stock,
                                #                         })
                                #                         inventory_wizard.change_product_qty()

                                #     if pro_var_flag == False:
                                #         print("pro_vals")
                                #         pro_vals = {
                                #             'product_tmpl_id': product_tmpl_id[0],
                                #             'product_template_attribute_value_ids': product_template_attribute_value_ids,
                                #             # 'list_price': child.get('price') or 0,
                                #             'marketplace_type': 'shopify',
                                #             'shopify_instance_id': instance_id.id,
                                #             'active': True,
                                #             'shopify_id': str(child['id']),
                                #             'default_code': child['sku'],
                                #             'barcode': child['barcode'] if child['barcode'] != '' else False,
                                #             'shopify_type': 'simple',
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
                                #         if marketplace_instance_id.sync_product_image == True:
                                #             pro_vals['image_1920'] = self.shopify_image_processing(
                                #                 child_file)

                                #         print("\npro_vals:\n", str(pro_vals))

                                #         if not VariantObj.sudo().search([('shopify_id', '=', str(child['id']))]):
                                #             prod_id = VariantObj.sudo().create(pro_vals)

                                #         _logger.info(
                                #             "product created %s", prod_id)
                                #         prod_id and existing_prod_ids.append(
                                #             str(child['id']))

                                #         if marketplace_instance_id.marketplace_fetch_quantity == True:
                                #             """Update Product Quantity in Odoo"""
                                #             product_stock = child['inventory_quantity']
                                #             # updating qty on hand
                                #             UpdateQtyWiz = self.env['stock.change.product.qty']
                                #             inventory_wizard = UpdateQtyWiz.create({
                                #                 'product_id': prod_id.id,
                                #                 'product_tmpl_id': prod_id.product_tmpl_id.id,
                                #                 'new_quantity': product_stock,
                                #             })
                                #             inventory_wizard.change_product_qty()
                                # else:
                                #     product = self.env['product.product']
                                #     current_product = product.search([("shopify_id", "=", str(child['id']))])
                                #     current_product.write({"shopify_instance_id": instance_id.id})

                            ###############################################################################
                            ###############################################################################
                    else:
                        image_file = False
                        for pic in product['images']:
                            if 'src' in pic:
                                image_file = pic.get('src')

                        prod_vals = {
                            'product_tmpl_id': product_tmpl_id[0],
                            'marketplace_type': 'shopify',
                            'shopify_instance_id': instance_id.id,
                            'shopify_id': str(product['id']),
                            'default_code': product.get('sku'),
                            'shopify_type': product.get('type_id') or 'simple',
                            'custom_option': False,
                            'combination_indices': self.get_variant_combs(child),
                        }
                        if marketplace_instance_id.sync_product_image == True:
                            prod_vals['image_1920'] = self.shopify_image_processing(
                                image_file)

                        if not VariantObj.sudo().search([('shopify_id', '=', str(product['id']))]):
                            prod_id = VariantObj.sudo().create(prod_vals)

                        _logger.info("product created %s", prod_id)
                        prod_id and existing_prod_ids.append(
                            str(product['id']))

                    print("Variants creation Ends")

                    self.env.cr.commit()
                    
                    # print("Catergory creation Starts")
                    # for categ in c_ids:
                    #     print(categ[0], product_tmpl_id[0])
                    #     categ_id = self.env['product.category'].sudo().search([
                    #         ('name', '=', categ[0])
                    #     ], limit=1)
                    #     cr.execute("insert into shopify_product_category(name,"
                    #                "categ_name, product_tmpl_id)"
                    #                " values (%s,%s,%s)",
                    #                (categ_id.id, categ[0], product_tmpl_id[0]))
                    # print("Catergory creation Ends")
                    # return existing_prod_ids

                except Exception as e:
                    _logger.warning("Exception-{}".format(e.args))
            else:

                product_obj = self.env['product.template']
                current_product = product_obj.search([("shopify_id","=",str(product['id']))])
                current_product.write({"shopify_instance_id":instance_id.id})
                if product_type == 'configurable_product':
                    current_product.product_variant_ids.write({"shopify_instance_id":instance_id.id})




    def find_default_vals(self, model_name):
        """
        Finds the default, required, database persistant fields for the model provided.
        Useful for creating records using query.
        """
        cr = self._cr
        cr.execute("select id from ir_model "
                   "where model=%s",
                   (model_name,))
        model_res = cr.fetchone()

        if not model_res:
            return
        cr.execute("select name from ir_model_fields "
                   "where model_id=%s and required=True "
                   " and store=True",
                   (model_res[0],))
        res = cr.fetchall()
        fields_list = [i[0] for i in res if res] or []
        Obj = self.env[model_name]
        default_vals = Obj.default_get(fields_list)

        return default_vals


    def check_for_new_attrs(self, template_id, variant):
        context = dict(self._context or {})
        product_template = self.env['product.template']
        product_attribute_line = self.env['product.template.attribute.line']
        all_values = []
        # attributes = variant.name_value
        attributes = variant

        for attribute in attributes:
            # for attribute_id in eval(attributes):
            attribute_id = attribute.get('name')  # 'Color'
            attribute_names = attribute.get('values')
            product_attribute_id = self.get_product_attribute_id(attribute_id)
            product_attribute_value_id = self.get_product_attribute_value_id(
                attribute_id,
                product_attribute_id.ids,
                template_id,
                attribute_names
            )

            exists = product_attribute_line.search(
                [
                    ('product_tmpl_id', '=', template_id.id),
                    ('attribute_id', 'in', product_attribute_id.ids)
                ]
            )
            if exists:
                pal_id = exists[0]
            else:
                pal_id = product_attribute_line.create(
                    {
                        'product_tmpl_id': template_id.id,
                        'attribute_id': product_attribute_id.id,
                        'value_ids': [[4, product_attribute_value_id]]
                    }
                )

            value_ids = pal_id.value_ids.ids
            for product_attribute_value_id in product_attribute_value_id.ids:
                if product_attribute_value_id not in value_ids:
                    pal_id.write(
                        {'value_ids': [[4, product_attribute_value_id]]})

                    PtAv = self.env['product.template.attribute.value']
                    domain = [
                        ('attribute_id', 'in', product_attribute_id.ids),
                        ('attribute_line_id', '=', pal_id.id),
                        ('product_attribute_value_id',
                         '=', product_attribute_value_id),
                        ('product_tmpl_id', '=', template_id.id)
                    ]

                    attvalue = PtAv.search(domain)

                    if len(attvalue) == 0:
                        product_template_attribute_value_id = PtAv.create({
                            'attribute_id': product_attribute_id.id,
                            'attribute_line_id': pal_id.id,  # attribute_line_id.id,
                            'product_attribute_value_id': product_attribute_value_id,
                            'product_tmpl_id': template_id.id,
                        })

                        all_values.append(
                            product_template_attribute_value_id.id)
        return [(6, 0, all_values)]



    def get_product_attribute_id(self, attribute_name):
        attrib_id = self.env['product.attribute'].search(
            [('name', '=', attribute_name)])
        # -------------------------Newly Added---------------------------
        if attribute_name == 'Title' and len(attrib_id) == 0:
            attrib_id = self.env['product.attribute'].sudo().create(
                {
                    'create_variant': 'no_variant',
                    'display_type': 'radio',
                    'name': attribute_name,
                }
            )
        # -------------------------Newly Added---------------------------
        return attrib_id


    def get_product_attribute_value_id(self, attribute_id, product_attribute_id, template_id, attribute_names):
        att_val_id = self.env['product.attribute.value'].search(
            [('attribute_id', 'in', product_attribute_id),
             ('name', 'in', attribute_names),
             ])
        return att_val_id

    

    def _shopify_update_attributes(self, odoo_attributes, options, attributes):
        cr = self._cr
        options = [str(i['attribute_id']) for i in options]

        for att in attributes:

            _logger.info("\natt['attribute_code']==>" +
                         str(att['attribute_id']))

            if str(att['attribute_id']) not in odoo_attributes and str(
                    att['attribute_id']) in options:

                # Check Attribureid in database
                print(att['attribute_code'])
                domain = [('name', '=', att['attribute_code'])]
                PA = self.env['product.attribute']
                rec = PA.sudo().search(domain)
                if rec:
                    cr.execute(
                        "select id from product_attribute where id=%s", (rec.id,))
                    rec_id = cr.fetchone()
                else:
                    cr.execute(
                        "insert into product_attribute (name,create_variant,display_type,marketplace_type) "
                        " values(%s, FALSE, 'radio', 'shopify') returning id",
                        (att['attribute_code'],))
                    rec_id = cr.fetchone()
                odoo_attributes[str(att['attribute_id'])] = {
                    'id': rec_id[0],  # id of the attribute in odoo
                    'code': att['attribute_code'],  # label
                    'options': {}
                }

            # attribute values
            if str(att['attribute_id']) in options:
                odoo_att = odoo_attributes[str(att['attribute_id'])]
                for opt in att['options']:
                    if opt != '' and opt != None \
                            and opt not in odoo_att['options']:

                        query = "Select id from product_attribute_value where name='" + opt + "' AND attribute_id='" + \
                            str(odoo_att['id']) + \
                            "' AND marketplace_type='shopify'"
                        cr.execute(query)
                        rec_id = cr.fetchone()

                        if not rec_id:
                            cr.execute(
                                "insert into product_attribute_value (name, attribute_id, marketplace_type)  "
                                "values(%s, %s, 'shopify') returning id",
                                (opt, odoo_att['id']))
                            rec_id = cr.fetchone()

                        # linking id in shopify with id in odoo
                        odoo_att['options'][str(opt)] = rec_id[0]

        return odoo_attributes

    # def _shopify_fetch_products(self):
    #     """Fetch products"""
    #     if self.fetch_type == 'to_odoo':
    #         # fetch products to odoo
    #         self.fetch_products_to_odoo()

    #     elif self.fetch_type == 'from_odoo':
    #         # update products to shopify
    #         # we will select all the products which are created locally
    #         self.fetch_products_from_odoo()

    def get_product_data(self):
        catalog_data = []
        products = self.env['product.product'].search([
            ('marketplace_type', '=', 'shopify'),
            ('default_code', '!=', None)
        ])

        if products:
            for product in products:
                product_data = {
                    "sku": product.default_code,
                    "name": product.name,
                    "price": product.list_price,
                    "attribute_set_id": 4,
                    "type_id": "simple"
                }
                catalog_data.append({"product": product_data})
        return catalog_data and [catalog_data, products] or None

    def shopify_fetch_products_to_odoo(self, kwargs):
        update_products_no = 0
        sp_product_list = []
        existing_ids = []
        cr = self._cr
        # fetching products already fetched from shopify to skip those already created
        cr.execute("select shopify_id from product_template "
                   "where shopify_id is not null ")
        products = cr.fetchall()
        ids = [str(i[0]) for i in products] if products else []

        cr.execute("select shopify_id from product_product "
                   "where shopify_id is not null")
        products = cr.fetchall()
        for i in products:
            ids.append(i[0]) if i[0] not in ids else None

        print("Odoo Product ids")
        print(products)

        categ_list = []

        if len(kwargs.get('marketplace_instance_id')) > 0:
            marketplace_instance_id = kwargs.get('marketplace_instance_id')
            version = '2021-01'
            version = marketplace_instance_id.marketplace_api_version
            url = marketplace_instance_id.marketplace_host + \
                '/admin/api/%s/products.json' % version

            if kwargs.get('fetch_o_product'):
                # /admin/api/2021-04/products/{product_id}.json
                url = marketplace_instance_id.marketplace_host + \
                    '/admin/api/%s/products/%s.json' % (
                        version, kwargs.get('product_id'))

            _logger.info("Product URL-->" + str(url))

            headers = {
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password}
            type_req = 'GET'

            configurable_products,next_link = self.env[
                'marketplace.connector'].shopify_api_call(
                headers=headers,
                url=url,
                type=type_req,
                marketplace_instance_id=marketplace_instance_id
            )

            # Update Product Categories
            # in shopify, each product can have one product type(category), so we are fetching all the product types
            # from shopify
            # and creating those in odoo. For the products updated from shopify,
            # we will be showing all the shopify categories in a separate field

        len_products = 0
        try:
            attributes = {}
            attributes['items'] = []

            simple_products = {}
            simple_products['items'] = []

            tmpl_vals = self.find_default_vals('product.template')
            simple_products_list = []

            if configurable_products.get('products'):
                sp_product_list = configurable_products.get('products')
            else:
                sp_product_list = [configurable_products.get('product')] if type(configurable_products.get('products')) != list else configurable_products.get('products')


            if configurable_products.get('errors') and 'products.fetch.wizard' in self._name:
                errors = "Error: %s".format(configurable_products.get('errors'))
                _logger.warning(errors)
                raise UserError(_(errors))
            ###############################################################
            #Create Feed Order from Shopify################################
            ###############################################################
            if not configurable_products.get('errors'):
                for sp_product in sp_product_list:
                    self.create_feed_parent_product(sp_product, marketplace_instance_id)
            ###############################################################
            update_products_no = len(sp_product_list)

            # from pprint import pprint
            # pprint(sp_product_list)

            for con_pro in sp_product_list:
                if con_pro.get('product_type') not in categ_list and con_pro.get('product_type') != '':
                    categ_list.append(con_pro.get('product_type'))

                try:
                    self.shopify_update_categories(categ_list)
                except Exception as e:
                    _logger.warning("Exception occured %s", e)
                    raise exceptions.UserError(_("Error Occured %s") % e)

                if len(con_pro.get('variants')) == 1:
                    simple_products['items'].append(con_pro)

                if con_pro.get('options'):
                    for option in con_pro.get('options'):
                        attribute = {}
                        attribute['attribute_id'] = str(option.get('id'))
                        attribute['label'] = str(option.get('name'))
                        attribute['attribute_code'] = str(option.get('name'))
                        attribute['options'] = option.get('values')
                        attributes['items'].append(attribute)

            simple_products_list = simple_products['items']

            _logger.info("start syncing simple products-->")
            if simple_products_list:
                existing_ids = self._shopify_import_products_list(
                    simple_products_list,
                    ids,
                    tmpl_vals,
                    attributes,
                    marketplace_instance_id,
                    'simple_product'
                )
            _logger.info("end syncing simple products-->")
            # end syncing simple products

            print("existing_ids")
            print(existing_ids)

            _logger.info("start syncing configurable products-->")
            # fetching child products of configurable products
            config_prod_list = []
            for product in sp_product_list:
                if len(product.get('variants')) > 0:
                    config_prod_list.append(product)

            # config_prod_list = configurable_products['products']
            # for config in config_prod_list:
            #     if len(config.get('variants'))> 1:
            #         config['childs'] = config.get('variants')

            # we have gathered configurable products with their childs
            # and the other simple products from shopify
            # next: first we will create all the configurable products with their variants

            # start creating configurable products
            # need to fetch the complete required fields list
            # and their values
            if config_prod_list:
                existing_ids = self._shopify_import_products_list(
                    config_prod_list,
                    ids,
                    tmpl_vals,
                    attributes,
                    marketplace_instance_id,
                    'configurable_product'
                )
            # end  creating configurable products
            _logger.info("existing_ids-->%s" % (existing_ids))
            _logger.info("end syncing configurable products-->")

        except Exception as e:
            _logger.info("Exception occured: %s", e)
            raise exceptions.UserError(_("Error Occured %s") % e)

        _logger.info("%d products are successfully updated." % update_products_no)

        # self.update_sync_history({
        #     'last_product_sync': '',
        #     'last_product_sync_id': sp_product_list[-1].get('id') if len(sp_product_list) > 0 else '',
        #     'product_sync_no': update_products_no,
        # })

        if kwargs.get('fetch_o_product'):
            """Return the Product ID"""
            return sp_product_list
        # else:
        #     return {
        #         'type': 'ir.actions.client',
        #         'tag': 'reload'
        #     }



    def update_sync_history(self, vals):
        from datetime import datetime
        SycnHis = self.env['marketplace.sync.history'].sudo()
        synhistory = SycnHis.search(
            [('marketplace_type', '=', 'shopify')], limit=1)
        if not synhistory:
            synhistory = SycnHis.search(
                [('marketplace_type', '=', 0)], limit=1)
            synhistory.write({'marketplace_type': 'shopify'})
        vals['last_product_sync'] = datetime.now()
        synhistory.write(vals)

    def shopify_fetch_products_from_odoo(self):
        url = '/rest/V1/products'
        type = 'POST'
        headers = {
            'Content-Type': 'application/json'
        }
        product_data = self.get_product_data()

        if not product_data:
            return
        updated_list = {}
        for product in product_data[0]:
            try:
                product_list,next_link = self.env[
                    'shopify.connector'].shopify_api_call(
                    headers=headers,
                    url=url,
                    type=type,
                    data=product
                )
                if product_list.get('sku'):
                    updated_list[product_list['sku']] = product_list.get(
                        'id')
            except:
                pass
        if updated_list:
            for product in product_data[1]:
                if product.default_code in updated_list:
                    product.write({
                        'marketplace_type': 'shopify',
                        'shopify_id': str(
                            updated_list[product.default_code])
                    })
                    product.product_tmpl_id.write({
                        'marketplace_type': 'shopify',
                        'shopify_id': str(
                            updated_list[product.default_code])
                    })
        _logger.info("%s product(s) updated", len(updated_list))
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def shopify_image_processing(self, image_url):
        if image_url:
            image = False
            if requests.get(image_url).status_code == 200:
                # print("image_url===>>>", image_url)
                image = base64.b64encode(requests.get(image_url).content)
                # print("image===>>>", image)
            return image
        else:
            return False

    def get_comb_indices(self, options):
        comb_indices = ''
        i = 1
        for value in [option.get('values') for option in options]:
            for cmb in value:
                if cmb not in comb_indices:
                    comb_indices += ',' + cmb if i != 1 else cmb
            i = 0 if i == 1 else 0
        print(comb_indices)
        return comb_indices
        # prints
        # Default Title,Red,Blue

    def get_variant_combs(self, child):
        comb_indices = False
        comb_arr = []
        for key, value in child.items():
            if key in ['option1', 'option2', 'option3']:
                if child[key] != None:
                    comb_arr.append(child[key])

        domain = [('name', 'in', comb_arr)]
        comb_indices = self.env['product.attribute.value'].search(domain)

        return comb_arr, comb_indices


    def create_feed_parent_product(self, product, instance_id):
        try:
            domain = [('parent', '=', True)]
            domain += [('shopify_id', '=', product['id'])]
            fp_product = self.env['shopify.feed.products'].sudo().search(domain)
            if not fp_product:
                record = self.env['shopify.feed.products'].sudo().create({
                    'instance_id': instance_id.id,
                    'parent': True,
                    'title': product['title'],
                    'shopify_id': product['id'],
                    'inventory_id': product.get('inventory_item_id'),
                    'barcode': product.get('barcode'),
                    'default_code': product.get('sku'),
                    'product_data': str(product),
                })
                record._cr.commit()
                _logger.info("Shopify Feed Parent Product Created-{}".format(record))
        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))


    def shopify_process_options(self, product, template):
        template['attribute_line_ids'] = []
        if product.get('options'):
            oprions = product.get('options')
            for option in oprions:
                PA = self.env['product.attribute']
                attribute_name = option.get('name')
                attribute_id = PA.sudo().search(
                    [('name', '=', option.get('name'))])
                if not attribute_id:
                    """Create Attribute"""
                    attribute_id = PA.sudo().create({
                        'create_variant': 'always',
                        'display_type': 'radio',
                        'name': attribute_name,
                    })

                values_ids = []
                values = option.get('values')
                for value in values:
                    PTV = self.env['product.attribute.value']
                    valud_id = PTV.sudo().search(
                        [('name', '=', value),("attribute_id","=",attribute_id.id)], limit=1)
                    if not valud_id:
                        valud_id = PTV.sudo().create({
                            'attribute_id': attribute_id.id,
                            'marketplace_type': 'shopify',
                            'name': value,
                        })
                    values_ids.append(valud_id.id)

                attribute_id.write({'value_ids': values_ids}) if value not in attribute_id.value_ids.mapped('name') else None

                template['attribute_line_ids'].append(
                    [0, 0,
                        {
                            'attribute_id': attribute_id.id,
                            'value_ids': [[6, False, values_ids]]
                        }
                    ])

        return template
