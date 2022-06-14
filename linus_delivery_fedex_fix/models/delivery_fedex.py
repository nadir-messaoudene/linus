# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time

from odoo import api, models, fields, _, tools
from odoo.exceptions import UserError
from odoo.tools import pdf

from odoo.addons.delivery_fedex.models.fedex_request import FedexRequest


_logger = logging.getLogger(__name__)

# Why using standardized ISO codes? It's way more fun to use made up codes...
# https://www.fedex.com/us/developer/WebHelp/ws/2014/dvg/WS_DVG_WebHelp/Appendix_F_Currency_Codes.htm
FEDEX_CURR_MATCH = {
    u'UYU': u'UYP',
    u'XCD': u'ECD',
    u'MXN': u'NMP',
    u'KYD': u'CID',
    u'CHF': u'SFR',
    u'GBP': u'UKL',
    u'IDR': u'RPA',
    u'DOP': u'RDD',
    u'JPY': u'JYE',
    u'KRW': u'WON',
    u'SGD': u'SID',
    u'CLP': u'CHP',
    u'JMD': u'JAD',
    u'KWD': u'KUD',
    u'AED': u'DHS',
    u'TWD': u'NTD',
    u'ARS': u'ARN',
    u'LVL': u'EURO',
}

FEDEX_STOCK_TYPE = [
    ('PAPER_4X6', 'PAPER_4X6'),
    ('PAPER_4X6.75', 'PAPER_4X6.75'),
    ('PAPER_4X8', 'PAPER_4X8'),
    ('PAPER_4X9', 'PAPER_4X9'),
    ('PAPER_7X4.75', 'PAPER_7X4.75'),
    ('PAPER_8.5X11_BOTTOM_HALF_LABEL', 'PAPER_8.5X11_BOTTOM_HALF_LABEL'),
    ('PAPER_8.5X11_TOP_HALF_LABEL', 'PAPER_8.5X11_TOP_HALF_LABEL'),
    ('PAPER_LETTER', 'PAPER_LETTER'),
    ('STOCK_4X6', 'STOCK_4X6'),
    ('STOCK_4X6.75', 'STOCK_4X6.75'),
    ('STOCK_4X6.75_LEADING_DOC_TAB', 'STOCK_4X6.75_LEADING_DOC_TAB'),
    ('STOCK_4X6.75_TRAILING_DOC_TAB', 'STOCK_4X6.75_TRAILING_DOC_TAB'),
    ('STOCK_4X8', 'STOCK_4X8'),
    ('STOCK_4X9', 'STOCK_4X9'),
    ('STOCK_4X9_LEADING_DOC_TAB', 'STOCK_4X9_LEADING_DOC_TAB'),
    ('STOCK_4X9_TRAILING_DOC_TAB', 'STOCK_4X9_TRAILING_DOC_TAB')
]


class ProviderFedex(models.Model):
    _inherit = 'delivery.carrier'

    def _fedex_convert_size(self, dimensions, unit='IN'):
        size_uom_id = self.env['product.template']._get_length_uom_id_from_ir_config_parameter()
        target_uom_unit = 'uom.product_uom_cm' if unit == 'CM' else 'uom.product_uom_inch'
        width = size_uom_id._compute_quantity(dimensions.width, self.env.ref(target_uom_unit), round=False)
        height = size_uom_id._compute_quantity(dimensions.height, self.env.ref(target_uom_unit), round=False)
        length = size_uom_id._compute_quantity(dimensions.packaging_length, self.env.ref(target_uom_unit), round=False)
        width = round(width)
        height = round(height)
        length = round(length)
        return width, height, length


#     def fedex_send_shipping(self, pickings):
#         res = []

#         for picking in pickings:

#             srm = FedexRequest(self.log_xml, request_type="shipping", prod_environment=self.prod_environment)
#             superself = self.sudo()
#             srm.web_authentication_detail(superself.fedex_developer_key, superself.fedex_developer_password)
#             srm.client_detail(superself.fedex_account_number, superself.fedex_meter_number)

#             srm.transaction_detail(picking.id)

#             # package_type = picking.package_ids and picking.package_ids[0].package_type_id.shipper_package_code or self.fedex_default_package_type_id.shipper_package_code
#             package_type = False
#             if picking.package_ids and picking.package_ids[0].package_type_id:
#                 package_type = picking.package_ids[0].package_type_id
#             else:
#                 package_type = self.fedex_default_package_type_id
#             srm.shipment_request(self.fedex_droppoff_type, self.fedex_service_type, package_type, self.fedex_weight_unit, self.fedex_saturday_delivery)
#             srm.set_currency(_convert_curr_iso_fdx(picking.company_id.currency_id.name))
#             srm.set_shipper(picking.company_id.partner_id, picking.picking_type_id.warehouse_id.partner_id)
#             srm.set_recipient(picking.partner_id)

#             srm.shipping_charges_payment(superself.fedex_account_number)

#             srm.shipment_label('COMMON2D', self.fedex_label_file_type, self.fedex_label_stock_type, 'TOP_EDGE_OF_TEXT_FIRST', 'SHIPPING_LABEL_FIRST')

#             order = picking.sale_id
#             company = order.company_id or picking.company_id or self.env.company
#             order_currency = picking.sale_id.currency_id or picking.company_id.currency_id

#             net_weight = self._fedex_convert_weight(picking.shipping_weight, self.fedex_weight_unit)

#             # Commodities for customs declaration (international shipping)
#             if 'INTERNATIONAL' in self.fedex_service_type or (picking.partner_id.country_id.code == 'IN' and picking.picking_type_id.warehouse_id.partner_id.country_id.code == 'IN'):

#                 commodity_currency = order_currency
#                 total_commodities_amount = 0.0
#                 commodity_country_of_manufacture = picking.picking_type_id.warehouse_id.partner_id.country_id.code

#                 for product in picking.move_line_ids.mapped('product_id'):
#                     related_operations = picking.move_line_ids.filtered(lambda ml: ml.product_id == product)
#                     commodity_quantity = sum(related_operations.mapped('qty_done'))
#                     commodity_amount = sum([round(operation.sale_price / (commodity_quantity or 1), 2) for operation in related_operations])
#                     total_commodities_amount += (commodity_amount * commodity_quantity)
#                     commodity_description = product.name
#                     commodity_number_of_piece = '1'
#                     commodity_weight_units = self.fedex_weight_unit
#                     commodity_weight_value = self._fedex_convert_weight(product.weight * commodity_quantity, self.fedex_weight_unit)
#                     commodity_quantity_units = 'EA'
#                     commodity_harmonized_code = product.hs_code or ''
#                     srm.commodities(_convert_curr_iso_fdx(commodity_currency.name), commodity_amount, commodity_number_of_piece, commodity_weight_units, commodity_weight_value, commodity_description, commodity_country_of_manufacture, commodity_quantity, commodity_quantity_units, commodity_harmonized_code)
#                 srm.customs_value(_convert_curr_iso_fdx(commodity_currency.name), total_commodities_amount, "NON_DOCUMENTS")
#                 srm.duties_payment(picking.picking_type_id.warehouse_id.partner_id, superself.fedex_account_number, superself.fedex_duty_payment)
#                 send_etd = superself.env['ir.config_parameter'].get_param("delivery_fedex.send_etd")
#                 srm.commercial_invoice(self.fedex_document_stock_type, send_etd)

#             package_count = len(picking.package_ids) or 1

#             # For india picking courier is not accepted without this details in label.
#             po_number = order.display_name or False
#             dept_number = False
#             if picking.partner_id.country_id.code == 'IN' and picking.picking_type_id.warehouse_id.partner_id.country_id.code == 'IN':
#                 po_number = 'B2B' if picking.partner_id.commercial_partner_id.is_company else 'B2C'
#                 dept_number = 'BILL D/T: SENDER'

#             # TODO RIM master: factorize the following crap

#             ################
#             # Multipackage #
#             ################
#             if package_count > 1:

#                 # Note: Fedex has a complex multi-piece shipping interface
#                 # - Each package has to be sent in a separate request
#                 # - First package is called "master" package and holds shipping-
#                 #   related information, including addresses, customs...
#                 # - Last package responses contains shipping price and code
#                 # - If a problem happens with a package, every previous package
#                 #   of the shipping has to be cancelled separately
#                 # (Why doing it in a simple way when the complex way exists??)

#                 master_tracking_id = False
#                 package_labels = []
#                 carrier_tracking_ref = ""

#                 for sequence, package in enumerate(picking.package_ids, start=1):

#                     package_width, package_height, package_length = self._fedex_convert_size(package_type)
#                     package_weight = self._fedex_convert_weight(package.shipping_weight, self.fedex_weight_unit)
#                     package_type = package.package_type_id
#                     srm._add_package(
#                         package_weight,
#                         package_code=package_type.shipper_package_code,
#                         package_height=package_height,
#                         package_width=package_width,
#                         package_length=package_length,
#                         sequence_number=sequence,
#                         po_number=po_number,
#                         dept_number=dept_number,
#                         reference=picking.display_name,
#                     )
#                     srm.set_master_package(net_weight, package_count, master_tracking_id=master_tracking_id)
#                     request = srm.process_shipment()
#                     package_name = package.name or sequence

#                     warnings = request.get('warnings_message')
#                     if warnings:
#                         _logger.info(warnings)

#                     # First package
#                     if sequence == 1:
#                         if not request.get('errors_message'):
#                             master_tracking_id = request['master_tracking_id']
#                             package_labels.append((package_name, srm.get_label()))
#                             carrier_tracking_ref = request['tracking_number']
#                         else:
#                             raise UserError(request['errors_message'])

#                     # Intermediary packages
#                     elif sequence > 1 and sequence < package_count:
#                         if not request.get('errors_message'):
#                             package_labels.append((package_name, srm.get_label()))
#                             carrier_tracking_ref = carrier_tracking_ref + "," + request['tracking_number']
#                         else:
#                             raise UserError(request['errors_message'])

#                     # Last package
#                     elif sequence == package_count:
#                         # recuperer le label pdf
#                         if not request.get('errors_message'):
#                             package_labels.append((package_name, srm.get_label()))

#                             carrier_price = self._get_request_price(request['price'], order, order_currency)

#                             carrier_tracking_ref = carrier_tracking_ref + "," + request['tracking_number']

#                             logmessage = _("Shipment created into Fedex<br/>"
#                                            "<b>Tracking Numbers:</b> %s<br/>"
#                                            "<b>Packages:</b> %s") % (carrier_tracking_ref, ','.join([pl[0] for pl in package_labels]))
#                             if self.fedex_label_file_type != 'PDF':
#                                 attachments = [('LabelFedex-%s.%s' % (pl[0], self.fedex_label_file_type), pl[1]) for pl in package_labels]
#                             if self.fedex_label_file_type == 'PDF':
#                                 attachments = [('LabelFedex.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
#                             picking.message_post(body=logmessage, attachments=attachments)
#                             shipping_data = {'exact_price': carrier_price,
#                                              'tracking_number': carrier_tracking_ref}
#                             res = res + [shipping_data]
#                         else:
#                             raise UserError(request['errors_message'])

#             # TODO RIM handle if a package is not accepted (others should be deleted)

#             ###############
#             # One package #
#             ###############
#             elif package_count == 1:
#                 package_type = picking.package_ids[:1].package_type_id or picking.carrier_id.fedex_default_package_type_id
#                 package_width, package_height, package_length = self._fedex_convert_size(package_type)
#                 srm._add_package(
#                     net_weight,
#                     package_code=package_type.shipper_package_code,
#                     package_height=package_height,
#                     package_width=package_width,
#                     package_length=package_length,
#                     po_number=po_number,
#                     dept_number=dept_number,
#                     reference=picking.display_name,
#                 )
#                 srm.set_master_package(net_weight, 1)

#                 # Ask the shipping to fedex
#                 request = srm.process_shipment()

#                 warnings = request.get('warnings_message')
#                 if warnings:
#                     _logger.info(warnings)

#                 if not request.get('errors_message'):

#                     if _convert_curr_iso_fdx(order_currency.name) in request['price']:
#                         carrier_price = request['price'][_convert_curr_iso_fdx(order_currency.name)]
#                     else:
#                         _logger.info("Preferred currency has not been found in FedEx response")
#                         company_currency = picking.company_id.currency_id
#                         if _convert_curr_iso_fdx(company_currency.name) in request['price']:
#                             amount = request['price'][_convert_curr_iso_fdx(company_currency.name)]
#                             carrier_price = company_currency._convert(
#                                 amount, order_currency, company, order.date_order or fields.Date.today())
#                         else:
#                             amount = request['price']['USD']
#                             carrier_price = company_currency._convert(
#                                 amount, order_currency, company, order.date_order or fields.Date.today())

#                     carrier_tracking_ref = request['tracking_number']
#                     logmessage = (_("Shipment created into Fedex <br/> <b>Tracking Number : </b>%s") % (carrier_tracking_ref))

#                     fedex_labels = [('LabelFedex-%s-%s.%s' % (carrier_tracking_ref, index, self.fedex_label_file_type), label)
#                                     for index, label in enumerate(srm._get_labels(self.fedex_label_file_type))]
#                     if picking.sale_id:
#                         for pick in picking.sale_id.picking_ids:
#                             pick.message_post(body=logmessage, attachments=fedex_labels)
#                     else:
#                         picking.message_post(body=logmessage, attachments=fedex_labels)
#                     shipping_data = {'exact_price': carrier_price,
#                                      'tracking_number': carrier_tracking_ref}
#                     res = res + [shipping_data]
#                 else:
#                     raise UserError(request['errors_message'])

#             ##############
#             # No package #
#             ##############
#             else:
#                 raise UserError(_('No packages for this picking'))
#             if self.return_label_on_delivery:
#                 self.get_return_label(picking, tracking_number=request['tracking_number'], origin_date=request['date'])
#             commercial_invoice = srm.get_document()
#             if commercial_invoice:
#                 fedex_documents = [('DocumentFedex.pdf', commercial_invoice)]
#                 picking.message_post(body='Fedex Documents', attachments=fedex_documents)
#         return res

# def _convert_curr_fdx_iso(code):
#     curr_match = {v: k for k, v in FEDEX_CURR_MATCH.items()}
#     return curr_match.get(code, code)

# def _convert_curr_iso_fdx(code):
#     return FEDEX_CURR_MATCH.get(code, code)


