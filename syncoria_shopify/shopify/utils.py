# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import pprint
import re
import json
import requests
from odoo import models, api, fields, tools, exceptions, _
from odoo import exceptions
import logging

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


def get_provar_vals(record, values):
    data = {}
    product = {
        'id': record.shopify_id,
        # 'product_id': 6929081696441,
        'title': record.name,
        'price': record.list_price,
        'sku': record.default_code,
        # 'position': 1,
        # 'inventory_policy': 'deny',
        'compare_at_price': record.shopify_compare_price,
        # 'fulfillment_service': 'manual',
        # 'inventory_management': None,
        # 'option1': 'Default Title',
        # 'option2': None,
        # 'option3': None,
        'taxable': record.shopify_charge_tax,
        'status': record.shopify_product_status,
        'barcode': record.barcode,
        # 'grams': 0,
        # 'image_id': None,
        'weight': record.weight,
        'weight_unit': record.uom_id.name,
        # 'inventory_item_id': 42940912238777,
        'inventory_quantity': record.qty_available,
        # 'old_inventory_quantity': 0,
        'requires_shipping': True if record.type == 'product' else False
    }
    if record.qty_available:
        product['inventory_quantity'] = int(record.qty_available)

    product = {k: v for k, v in product.items() if v}
    data["product"] = product
    return data


def get_protmpl_vals(record, values):
    VariantObj = record.env['product.product'].sudo()
    data = {}
    product = {}
    body_html = record.description_sale or ''

    product.update({
        "title": record.name,
        "body_html": body_html,
        "vendor": record.shopify_vendor or "",
        "product_type": record.categ_id.name or "",
        "status": record.shopify_product_status,
    })
    instance_id = record.shopify_instance_id
    if not instance_id:
        instance_id = get_marketplace(record)
    print(instance_id)
    if 'product.template' in str(record):
        variants = []
        variants_rec = record.product_variant_ids
        
        for var in variants_rec:
            variant = {}
            count = 1
            hs_code = False
            try:
                hs_code = var.x_studio_customs_hs_code
                _logger.warning("hscode ===>>>%s", hs_code)
            except Exception as e:
                hs_code = var.hs_code
                _logger.warning("Exception ===>>>%s", e.args)

            shopify_price = var.lst_price
            if instance_id.pricelist_id.currency_id.id != var.currency_id.id:
                shopify_price = var.shopify_price
            
            for attrib in var.product_template_attribute_value_ids:
                _logger.info(attrib.attribute_id.name)
                _logger.info(attrib.name)
                variant["option" + str(count)] = attrib.name
                count += 1
                # Add Other Informations
                variant.update({
                    'id': var.shopify_id,
                    'title': var.name,
                    'price': shopify_price,
                    'sku': var.default_code,
                    'inventory_quantity': int(var.qty_available),
                    # 'position': 1,
                    # 'inventory_policy': 'deny',
                    # 'compare_at_price': None,
                    # 'fulfillment_service': 'manual',
                    'inventory_management': 'shopify',  # Track Inventory
                    # 'option1': 'Default Title',
                    # 'option2': None,
                    # 'option3': None,
                    # 'taxable': True,
                    'cost': var.standard_price,
                    'barcode': var.barcode,
                    # 'grams': 0,
                    # 'image_id': None,
                    'weight': var.weight,  # Variant weight
                    'weight_unit': var.weight_uom_name,  # Variant uom
                    # 'inventory_item_id': 42940912238777,
                    # 'old_inventory_quantity': 0,
                    # 'requires_shipping': True,
                })
                if record.qty_available:
                    product['inventory_quantity'] = int(record.qty_available)

                variant = {k: v for k, v in variant.items() if v}

            if len(variant) > 0:
                variants.append(variant)

        product["variants"] = variants
        options = []
        for att_line in record.attribute_line_ids:
            option = {}
            option["name"] = att_line.attribute_id.name
            option["values"] = []
            for value_id in att_line.value_ids:
                option["values"].append(value_id.name)
            options.append(option)

        product["options"] = options
    
    # Update Product Image
    if record.image_1920:
        product.update({
            "images": [{
                "attachment": record.image_1920.decode()
            }]
        })

    try:
        for image in record.product_template_image_ids:
            product['images'] += [{
                "attachment": image.image_1920.decode()
            }]
    except Exception as e:
        _logger.info("Exception-%s", e.args)
    single_product = False
    if "req_type" in values:
        single_product = True
        product.update({"id": record.shopify_id})
    # print(len(product['variants']))
    if 'variants' not in product or ('variants' in product and len(product['variants']) == 0):
        shopify_price = record.list_price
        if instance_id.pricelist_id.currency_id.id != record.currency_id.id:
            shopify_price = record.shopify_price
        product['variants'] = [{
            'title': record.name,
            'price': shopify_price,
            'sku': record.default_code,
            'barcode': record.barcode,
            'weight': record.weight,
            'weight_unit': record.weight_uom_name,
            'inventory_quantity': int(record.qty_available),
            'cost': record.standard_price,
            'inventory_management': 'shopify',
        }]
        if record.image_1920:
            product['variants'][0].update({
                "image": [{
                    "attachment": record.image_1920.decode() if record.image_1920 else ""
                }]
            })
        
        del product['product_type']
    else:
        shopify_price = record.list_price
        if instance_id.pricelist_id.currency_id.id != record.currency_id.id:
            shopify_price = record.shopify_price
        product.update({
            'id': record.shopify_id or "",
            'title': record.name,
            'price': shopify_price,
            'sku': record.default_code,
            'barcode': record.barcode,
            'weight': record.weight,
            'weight_unit': record.weight_uom_name,
            'inventory_quantity': record.qty_available,
        })

    print(product)
    print(values)
    print("data")
    print(data)

    marketplace_instance_id = get_marketplace(record)
    print(marketplace_instance_id)
    if marketplace_instance_id.set_price:
        product.update({"price": record.list_price})
    if marketplace_instance_id.set_stock and record.qty_available:
        product.update({"inventory_quantity": int(record.qty_available)})
    if product.get('images'):
        _logger.info("\images===>>>\n" + str(len(product['images'])))
    
    product = {k: v for k, v in product.items() if v}
    data["product"] = product


    # if 'product.product' in str(record):
    #     data = {}
    #     variant = {}

    #     #Product ID
    #     variant["product_id"] = record.product_tmpl_id.shopify_id
    #     variant["sku"] = record.default_code

    #     #Price
    #     shopify_price = record.list_price
    #     if instance_id.pricelist_id.currency_id.id != record.currency_id.id:
    #         shopify_price = record.shopify_price
    #     variant["price"] = shopify_price
    #     if marketplace_instance_id.set_price:
    #         variant.update({"price": record.list_price})

    #     #Attributes
    #     position = 1
    #     for att in record.product_template_variant_value_ids.sorted():
    #         value = record.env['product.attribute.value'].browse(att.product_attribute_value_id.id)
    #         variant['option' + str(position)] = value.name
    #         position += 1
        
    #     #Images
    #     # if record.image_1920:
    #     #     variant['image'] = [{
    #     #             "attachment": record.image_1920.decode() if record.image_1920 else ""
    #     #         }]

    #     data['variant'] = variant

    _logger.info("\nDATA===>>>\n" + pprint.pformat(data))
    
    return data

def get_protmpl_product_product_vals(record, instance_obj):
    data = {}
    if 'product.product' in str(record):
        variant = {}

        #Product ID
        variant["product_id"] = record.product_tmpl_id.shopify_id
        variant["sku"] = record.default_code

        #Price
        shopify_price = record.list_price
        if instance_obj.pricelist_id.currency_id.id != record.currency_id.id:
            shopify_price = record.shopify_price
        variant["price"] = shopify_price
        if instance_obj.set_price:
            variant.update({"price": record.list_price})

        #Attributes
        position = 1
        for att in record.product_template_variant_value_ids.sorted():
            value = record.env['product.attribute.value'].browse(att.product_attribute_value_id.id)
            variant['option' + str(position)] = value.name
            position += 1

        data['variant'] = variant
    
    return data


def shopify_update_variant(record, data):
    """This function updates Product Variant on Shopify using REST API

    Args:
        record (`product.product`): Variant Object
        data (`variant data`): Variant data
    """


def get_marketplace(record):
    """This function return the marketplace

    Args:
        record (`product.product`): Variant Object
    """
    ICPSudo = record.env['ir.config_parameter'].sudo()
    try:
        marketplace_instance_id = ICPSudo.get_param(
            'syncoria_base_marketplace.marketplace_instance_id')
        marketplace_instance_id = [int(s) for s in re.findall(
            r'\b\d+\b', marketplace_instance_id)]
    except:
        marketplace_instance_id = False
    if marketplace_instance_id:
        marketplace_instance_id = record.env['marketplace.instance'].sudo().search(
            [('id', '=', marketplace_instance_id[0])])
    return marketplace_instance_id


# def shopify_api_call(**kwargs):
#     """
#     We will be running the api calls from here
#     :param kwargs: dictionary with all the necessary parameters,
#     such as url, header, data,request type, etc
#     :return: response obtained for the api call
#     """
#     if kwargs.get('kwargs'):
#         kwargs = kwargs.get('kwargs')
#     if not kwargs:
#         # no arguments passed
#         return

#     type = kwargs.get('type') or 'GET'
#     complete_url = 'https://' + kwargs.get('url')
#     _logger.info("%s", complete_url)
#     headers = kwargs.get('headers')

#     data = json.dumps(kwargs.get('data')) if kwargs.get('data') else None
#     _logger.info("Request DATA==>>>" + pprint.pformat(data))

#     try:
#         res = requests.request(type, complete_url, headers=headers, data=data)
#         if res.status_code in [200, 201]:
#             _logger.warning(_("Error:" + str(res.text)))
#         items = json.loads(res.text) if res.status_code in [200, 201] else {
#             'errors': res.text if res.text != '' else 'Error: Empty response from Shopify\nResponse Code: %s' % (
#                 res.status_code)}
#         _logger.info("items==>>>" + pprint.pformat(items))
#         return items
#     except Exception as e:
#         _logger.info("Exception occured %s", e)
#         raise exceptions.UserError(_("Error Occured 5 %s") % e)

def shopify_api_call(**kwargs):
    """
    We will be running the api calls from here
    :param kwargs: dictionary with all the necessary parameters,
    such as url, header, data,request type, etc
    :return: response obtained for the api call
    """
    if kwargs.get('kwargs'):
        kwargs = kwargs.get('kwargs')
    if not kwargs:
        # no arguments passed
        return

    type = kwargs.get('type') or 'GET'
    complete_url = 'https://' + kwargs.get('url')
    _logger.info("%s", complete_url)
    headers = kwargs.get('headers')

    data = json.dumps(kwargs.get('data')) if kwargs.get('data') else None
    _logger.info("Request DATA==>>>" + pprint.pformat(data))

    params = {}
    if kwargs.get('params'):
        params = kwargs.get('params')

    try:
        res = requests.request(type, complete_url, headers=headers, data=data,params=params)
        next_link = res.links if hasattr(res, 'links') else None
        if res.status_code in [200, 201]:
            _logger.warning(_("Error:" + str(res.text)))
        items = json.loads(res.text) if res.status_code in [200, 201] else {
            'errors': res.text if res.text != '' else 'Error: Empty response from Shopify\nResponse Code: %s' % (
                res.status_code)}
        _logger.info("items==>>>" + pprint.pformat(items))
        return items,next_link
    except Exception as e:
        _logger.info("Exception occured %s", e)
        raise exceptions.UserError(_("Error Occured 5 %s") % e)


def update_product_images(record, product_data, req_type, marketplace_instance_obj=None):
    data = {}
    attachments = [record.image_1920.decode()] if record.image_1920 else []
    # try:
    #     for attachment in record.product_template_image_ids:
    #         attachments += record.product_template_image_ids if record.product_template_image_ids else []
    # except Exception as e:
    #     _logger.info("\nException--->\n" + str(attachments))
    if not record.shopify_image_id:
        req_type ='create'
    for attachment in attachments:
        data = {
            "image":
                {
                    "variant_ids":[record.shopify_id],
                    "attachment": attachment
                }
        }
        marketplace_instance_id = record.shopify_instance_id
        if marketplace_instance_obj:
            marketplace_instance_id = marketplace_instance_obj
        version = marketplace_instance_id.marketplace_api_version or '2021-01'
        url = marketplace_instance_id.marketplace_host
        if req_type == 'create':
            type_req = 'POST'
            # url += '/admin/api/%s/variants/%s.json' % (
            #     version, record.shopify_id)
            url += '/admin/api/%s/products/%s/images.json' % (
                version, product_data.shopify_id)
        if req_type == 'update':
            type_req = 'PUT'
            url += '/admin/api/%s/products/%s/images/%s.json' % (
                version, product_data.shopify_id,record.shopify_image_id)
        headers = {
            'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
            'Content-Type': 'application/json'
        }
        updated_products,next_link = shopify_api_call(
            headers=headers,
            url=url,
            type=type_req,
            marketplace_instance_id=marketplace_instance_id,
            data=data
        )
        if "errors" not in updated_products:
            var = record.write({
                "shopify_image_id": updated_products["image"]["id"]
            })


        # _logger.info("\updated_products--->\n" + str(updated_products))


def shopify_pt_request(record, data, req_type):
    if record.shopify_instance_id:
        marketplace_instance_id = record.shopify_instance_id
    else:
        marketplace_instance_id = get_marketplace(record)

    version = marketplace_instance_id.marketplace_api_version or '2021-01'
    url = marketplace_instance_id.marketplace_host

    if req_type == 'create' and 'product.template' in str(record):
        type_req = 'POST'
        url += '/admin/api/%s/products.json' % version
    if req_type == 'update' and 'product.template' in str(record):
        type_req = 'PUT'
        url += '/admin/api/%s/products/%s.json' % (version, record.shopify_id)
        if 'images' in data['product']:
            del data['product']['images']

    if req_type == 'create' and 'product.product' in str(record):
        type_req = 'POST'
        url += '/admin/api/%s/products/%s/variants.json' % (version, record.product_tmpl_id.shopify_id)
    if req_type == 'update' and 'product.product' in str(record):
        type_req = 'PUT'
        url += '/admin/api/%s/variants/%s.json' % (version, record.shopify_id)

    if 'product.product' in str(record) and data.get('product'):
        data = {}
        data['variant'] = data.get('product')

    headers = {
        'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
        'Content-Type': 'application/json'
    }
    created_products,next_link = shopify_api_call(
        headers=headers,
        url=url,
        type=type_req,
        marketplace_instance_id=marketplace_instance_id,
        data=data
    )
    _logger.info("\ncreated_products--->\n" + pprint.pformat(created_products))

    if created_products.get('errors'):
        raise exceptions.UserError(_(created_products.get('errors')))
    elif created_products.get('product', {}).get("id"):
        if not record.shopify_id:
            shopify_id = created_products.get("product").get("id")
            record.write(
                {'shopify_id': created_products.get("product").get("id")})

        if created_products.get('product', {}).get("variants"):
            if len(created_products.get('product', {}).get("variants")) == 1:
                varaint = created_products.get(
                    'product', {}).get("variants")[0]
                product_ids = record.env['product.product'].sudo().search(
                    [('product_tmpl_id', '=', record.id)])
                if len(product_ids) == 1:
                    vals = {
                        'shopify_id': varaint.get('id'),
                        'marketplace_type': 'shopify',
                        'shopify_inventory_id': varaint.get("inventory_item_id"),
                        'shopify_instance_id': marketplace_instance_id.id
                    }
                    product_ids[0].write(vals)
                else:
                    """"""
            if len(created_products.get('product', {}).get("variants")) > 1:
                """Update Variants for the Products"""
                variants = created_products.get('product', {}).get("variants")
                options = created_products.get('product', {}).get("options")
                options_dict = {}
                for opt in options:
                    if opt:
                        options_dict['option' +
                                     str(opt['position'])] = opt['name']

                for var in variants:
                    fields = list([key for key, value in var.items()])
                    pro_domain = []
                    ptav_ids = []
                    for key, value in options_dict.items():
                        if key in fields:
                            attribute_id = record.env['product.attribute'].sudo().search(
                                [('name', '=', value)], limit=1).id
                            domain = [('attribute_id', '=', attribute_id)]
                            # [FIX] Here we got multiple attribute value from different
                            # product template so I added for specific template
                            domain += [('name', '=', var[key]), ('product_tmpl_id', '=', record.id)]
                            ptav = record.env['product.template.attribute.value'].sudo().search(
                                domain, limit=1)
                            ptav_ids += ptav.ids
                    # [FIX] product I added extra condition product_tmpl

                    pro_domain += [('product_tmpl_id', '=', record.id)]
                    if len(ptav_ids) > 1:
                        for ptav_id in ptav_ids:
                                pro_domain += [('product_template_attribute_value_ids','=', ptav_id)]
                    elif len(ptav_ids) == 1:
                        pro_domain += [('product_template_attribute_value_ids',
                                        'in', ptav_ids)]


                    var_id = record.env['product.product'].sudo().search(
                        pro_domain, limit=1)
                    _logger.info("pro_domain-->%s", pro_domain)

                    if var_id:
                        var_id.write({
                            'shopify_id': var['id'],
                            'marketplace_type': 'shopify',
                            'shopify_inventory_id': var.get("inventory_item_id"),
                            'shopify_instance_id': marketplace_instance_id.id
                        })
                        _logger.info("var_id-->%s", var_id)
                        # Update Product Images
                        update_product_images(var_id, record, req_type)
        else:
            record.write(
                {'shopify_inventory_id': created_products.get("product").get("inventory_item_id")})
    

        body = _("Shopify Product " + req_type + " with Shopify ID: " +
                 str(created_products.get("product").get("id")))
        _logger.info(body)
        record.message_post(body=body)
    elif created_products.get('variant', {}).get("id"):
        if not record.shopify_id:
            record.write(
                {'shopify_id': created_products.get("variant").get("id"),
                'marketplace_type': 'shopify',
                'shopify_instance_id': marketplace_instance_id.id,
                'shopify_inventory_id': created_products.get("variant").get("inventory_item_id"),
                })
            update_product_images(record, record.product_tmpl_id, req_type)

        body = _("Shopify Product Variant " + req_type + " with Shopify ID: " +
                 str(created_products.get("variant").get("id")))
        _logger.info(body)
        record.message_post(body=body)

def shopify_pt_request_create_product_by_instance(record, data, req_type, marketplace_instance_id):
    default_marketplace_instance_id = get_marketplace(record)

    version = marketplace_instance_id.marketplace_api_version or '2021-01'
    url = marketplace_instance_id.marketplace_host


    if req_type == 'create' and 'product.product' in str(record):
        type_req = 'POST'
        url += '/admin/api/%s/products/%s/variants.json' % (version, record.product_tmpl_id.shopify_id)
    else:
        return

    if 'product.product' in str(record) and data.get('product'):
        data = {}
        data['variant'] = data.get('product')

    headers = {
        'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
        'Content-Type': 'application/json'
    }
    created_products,next_link = shopify_api_call(
        headers=headers,
        url=url,
        type=type_req,
        marketplace_instance_id=marketplace_instance_id,
        data=data
    )
    _logger.info("\ncreated_products--->\n" + pprint.pformat(created_products))

    if created_products.get('errors'):
        raise exceptions.UserError(_(created_products.get('errors')))
    elif created_products.get('variant', {}).get("id"):
        if not record.shopify_id and marketplace_instance_id == default_marketplace_instance_id:
            record.write(
                {'shopify_id': created_products.get("variant").get("id"),
                'marketplace_type': 'shopify',
                'shopify_instance_id': marketplace_instance_id.id,
                'shopify_inventory_id': created_products.get("variant").get("inventory_item_id"),
                })
            update_product_images(record, record.product_tmpl_id, req_type, marketplace_instance_id)
        if marketplace_instance_id != default_marketplace_instance_id:
            prod_mapping = record.env['shopify.multi.store'].sudo().search([('product_id', '=', record.id), ('shopify_instance_id', '=', marketplace_instance_id.id)])
            val_dict = {
                'name': created_products.get("variant").get('sku'),
                'shopify_instance_id': marketplace_instance_id.id,
                'product_id': record.id,
                'shopify_id': created_products.get("variant").get('id'),
                'shopify_parent_id': created_products.get("variant").get('product_id'),
                'shopify_inventory_id': created_products.get("variant").get('inventory_item_id')
            }
            if not prod_mapping:
                prod_mapping = record.env['shopify.multi.store'].sudo().create(val_dict)
            else:
                prod_mapping.write(val_dict)
            update_product_images(record, record.product_tmpl_id, req_type, marketplace_instance_id)

        body = _("Shopify Product Variant " + req_type + " with Shopify ID: " +
                 str(created_products.get("variant").get("id")) + " at Instance: " + marketplace_instance_id.name)
        _logger.info(body)
        record.message_post(body=body)


# --------------------------------------------------------------------------------------------------------
# --------------------------------------Shopify Customer Functions----------------------------------------
# --------------------------------------------------------------------------------------------------------

def shopify_address_values(record):
    address = {}
    first_name = record.name.split(' ', 1)[1] if len(
        record.name.split(' ', 1)[1]) > 0 else ''
    last_name = record.name.split(' ', 1)[1] if len(
        record.name.split(' ', 1)) > 1 else ''

    address = {
        "address": {
            "address1": record.street or '',
            "address2": record.street2 or '',
            "city": record.city or '',
            "company": "Fancy Co.",
            "first_name": first_name,
            "last_name": first_name,
            "phone": record.phone,
            "province": record.state_id.name if record.state_id else '',
            "country": record.country_id.name if record.country_id else '',
            "zip": record.zip,
            "name": record.name,
            "province_code": record.state_id.code if record.state_id else '',
            "country_code": record.country_id.code if record.country_id else '',
            "country_name": record.country_id.name if record.country_id else '',
        }
    }

    address = {k: v for k, v in address.items() if v}

    return address


def shopify_customer_values(record):
    first_name = record.name.split(' ')[0] if len(
        record.name.split(' ', 1)) > 0 else ''
    last_name = record.name.split(' ', 1)[1] if len(
        record.name.split(' ', 1)) > 1 else ''
    customer = {
        "customer": {
            "first_name": first_name,
            "last_name": last_name,
            "email": record.email or '',
            "phone": record.phone or '',
            # Fields can be added
            'note': record.comment,
            'accepts_marketing': record.shopify_accepts_marketing,
            'currency': record.currency_id.name,
            # 'marketing_opt_in_level' : record.currency_id.name,
        }
    }

    customer = {k: v for k, v in customer.items() if v}
    customer["customer"]["default_address"] = shopify_address_values(record)
    pprint.pprint(customer)
    return customer


def shopify_cus_req(self, data, req_type):
    """This function call SHopify Api to get Customer Informations

    Args:
        data (dict): A dict of Customer Information
        req_type (['search','create','update']): Request Type

    Returns:
        dict: Dict containing customer response
    """
    marketplace_instance_id = get_marketplace(self)
    version = marketplace_instance_id.marketplace_api_version or '2021-01'
    url = marketplace_instance_id.marketplace_host
    if req_type == 'create':
        type_req = 'POST'
        url += '/admin/api/%s/customers.json' % version
    if req_type == 'update':
        type_req = 'PUT'
        url += '/admin/api/%s/customers/%s.json' % (version, self.shopify_id)
    if req_type == 'delete':
        type_req = 'DELETE'
        url += '/admin/api/%s/customers/%s.json' % (version, self.shopify_id)
    if req_type == 'search':
        type_req = 'GET'
        url += '/admin/api/%s/customers/search.json?query=email:%s&fields=email,id' % (
            version, self.email)

    headers = {
        'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
        'Content-Type': 'application/json'
    }
    customer,next_link = self.env['marketplace.connector'].shopify_api_call(
        headers=headers,
        url=url,
        type=type_req,
        marketplace_instance_id=marketplace_instance_id,
        data=data
    )
    import json
    customer = json.dumps(customer)
    return customer


def shopify_add_req(self, data, req_type):
    """This function call Shopify Api to get Address Informations

    Args:
        data (dict): A dict of Address Information
        req_type (['search','create','update']): Request Type

    Returns:
        dict: Address Response
    """
    marketplace_instance_id = get_marketplace(self)
    version = marketplace_instance_id.marketplace_api_version or '2021-01'
    url = marketplace_instance_id.marketplace_host
    if req_type == 'create':
        type_req = 'POST'
        url += '/admin/api/%s/customers/%s/addresses.json' % (
            version, self.shopify_id)
    if req_type == 'update':
        type_req = 'PUT'
        url += '/admin/api/%s/customers/%s/addresses/%s.json' % (
            version, self.shopify_id, self.shopify_add_id)
    if req_type == 'delete':
        type_req = 'PUT'
        url += '/admin/api/%s/customers/%s/addresses/%s.json' % (
            version, self.shopify_id, self.shopify_add_id)

    if req_type == 'search':
        type_req = 'GET'
        url += '/admin/api/%s/customers/%s/addresses/%s.json' % (
            version, self.shopify_id, self.shopify_add_id)

    headers = {
        'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
        'Content-Type': 'application/json'
    }
    address,next_link = self.env['marketplace.connector'].shopify_api_call(
        headers=headers,
        url=url,
        type=type_req,
        marketplace_instance_id=marketplace_instance_id,
        data=data
    )
    import json
    address = json.dumps(address)
    return address


def shopify_inventory_request(record, data, req_type):
    marketplace_instance_id = get_marketplace(record)
    version = marketplace_instance_id.marketplace_api_version or '2022-01'
    url = marketplace_instance_id.marketplace_host

    # "https://your-development-store.myshopify.com/admin/api/2022-01/inventory_items/808950810.json"

    if req_type == 'create' and 'product.template' in str(record):
        type_req = 'POST'
        url += '/admin/api/%s/inventory_items/%s.json' %(version, record.shopify_inventory_id)
    if req_type == 'update' and 'product.template' in str(record):
        type_req = 'PUT'
        url += '/admin/api/%s/inventory_items/%s.json' %(version, record.shopify_inventory_id)

    if req_type == 'create' and 'product.product' in str(record):
        type_req = 'POST'
        url += '/admin/api/%s/inventory_items/%s.json' %(version, record.shopify_inventory_id)
    if req_type == 'update' and 'product.product' in str(record):
        type_req = 'PUT'
        url += '/admin/api/%s/inventory_items/%s.json' %(version, record.shopify_inventory_id)

    headers = {
        'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
        'Content-Type': 'application/json'
    }
    
    inventory_items,next_link = shopify_api_call(
        headers=headers,
        url=url,
        type=type_req,
        marketplace_instance_id=marketplace_instance_id,
        data=data
    )
    _logger.info("\inventory_items--->\n" + pprint.pformat(inventory_items))

    if inventory_items.get('errors'):
        raise exceptions.UserError(_(inventory_items.get('errors')))
    elif inventory_items.get('inventory_item', {}).get("id"):
        #         {
        # "inventory_item": {
        #     "id": 808950810,
        #     "sku": "IPOD2008PINK",
        #     "created_at": "2022-02-03T16:53:36-05:00",
        #     "updated_at": "2022-02-03T16:53:36-05:00",
        #     "requires_shipping": true,
        #     "cost": "25.00",
        #     "country_code_of_origin": null,
        #     "province_code_of_origin": null,
        #     "harmonized_system_code": null,
        #     "tracked": true,
        #     "country_harmonized_system_codes": [],
        #     "admin_graphql_api_id": "gid://shopify/InventoryItem/808950810"
        # }
        # }
        body = "Variant Updated for Id-%s" %(inventory_items.get('inventory_item', {}).get("id"))
        record.message_post(body=body)
