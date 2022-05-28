# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import psycopg2

from odoo import api, fields, models, registry, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)

#USPS, Fedex and UPS
class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    mapping_carrier_service_3pl_ids = fields.One2many('mapping.carrier.service.3pl', 'delivery_carrier_id', string='Facilities')

class MappingCarrierService3pl(models.Model):
    _name = 'mapping.carrier.service.3pl'
    _description = "Mapping Carrier Service 3PL"

    delivery_carrier_id = fields.Many2one('delivery.carrier', 'Delivery Carrier')

    delivery_type = fields.Selection(string='Provider', related='delivery_carrier_id.delivery_type')
    fedex_service_type = fields.Selection([('INTERNATIONAL_ECONOMY', 'INTERNATIONAL_ECONOMY'),
                                           ('INTERNATIONAL_PRIORITY', 'INTERNATIONAL_PRIORITY'),
                                           ('FEDEX_GROUND', 'FEDEX_GROUND'),
                                           ('FEDEX_2_DAY', 'FEDEX_2_DAY'),
                                           ('FEDEX_2_DAY_AM', 'FEDEX_2_DAY_AM'),
                                           ('FEDEX_3_DAY_FREIGHT', 'FEDEX_3_DAY_FREIGHT'),
                                           ('FIRST_OVERNIGHT', 'FIRST_OVERNIGHT'),
                                           ('PRIORITY_OVERNIGHT', 'PRIORITY_OVERNIGHT'),
                                           ('STANDARD_OVERNIGHT', 'STANDARD_OVERNIGHT'),
                                           ('FEDEX_NEXT_DAY_EARLY_MORNING', 'FEDEX_NEXT_DAY_EARLY_MORNING'),
                                           ('FEDEX_NEXT_DAY_MID_MORNING', 'FEDEX_NEXT_DAY_MID_MORNING'),
                                           ('FEDEX_NEXT_DAY_AFTERNOON', 'FEDEX_NEXT_DAY_AFTERNOON'),
                                           ('FEDEX_NEXT_DAY_END_OF_DAY', 'FEDEX_NEXT_DAY_END_OF_DAY'),
                                           ('FEDEX_EXPRESS_SAVER', 'FEDEX_EXPRESS_SAVER'),
                                           ],
                                          default='INTERNATIONAL_PRIORITY')
    usps_domestic_regular_container = fields.Selection([('Flat Rate Envelope', 'Flat Rate Envelope'),
                                                        ('Sm Flat Rate Envelope', 'Small Flat Rate Envelope'),
                                                        ('Legal Flat Rate Envelope', 'Legal Flat Rate Envelope'),
                                                        ('Padded Flat Rate Envelope', 'Padded Flat Rate Envelope'),
                                                        ('Flat Rate Box', 'Flat Rate Box'),
                                                        ('Sm Flat Rate Box', 'Small Flat Rate Box'),
                                                        ('Lg Flat Rate Box', 'Large Flat Rate Box'),
                                                        ('Md Flat Rate Box', 'Medium Flat Rate Box')],
                                                       string="Type of USPS domestic regular container", default="Lg Flat Rate Box")
    ups_default_service_type = fields.Selection([('03', 'UPS Ground'),
                                                ('11', 'UPS Standard'),
                                                ('01', 'UPS Next Day'),
                                                ('14', 'UPS Next Day AM'),
                                                ('13', 'UPS Next Day Air Saver'),
                                                ('02', 'UPS 2nd Day'),
                                                ('59', 'UPS 2nd Day AM'),
                                                ('12', 'UPS 3-day Select'),
                                                ('65', 'UPS Saver'),
                                                ('07', 'UPS Worldwide Express'),
                                                ('08', 'UPS Worldwide Expedited'),
                                                ('54', 'UPS Worldwide Express Plus'),
                                                ('96', 'UPS Worldwide Express Freight')
                                            ], string="UPS Service Type", default='03')
    carrier_service_3pl_id = fields.Many2one('carrier.services.3pl', '3PL Carrier Service')