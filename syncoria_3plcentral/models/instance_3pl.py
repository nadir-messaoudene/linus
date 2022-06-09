from importlib import resources
from pyexpat import model
from odoo import models, fields
import requests, json
from requests.auth import HTTPBasicAuth
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class Facilities3PL(models.Model):
    _name = 'facilities.3pl'
    _description = "Facilities 3PL"

    name = fields.Char(string='Name', required=True)
    facilityId = fields.Integer(string="Facility ID")
    instance_3pl_id = fields.Many2one('instance.3pl', 'Instance')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    _sql_constraints = [
        (
            'unique_warehouse_byfacility',
            'UNIQUE(facilityId, warehouse_id)',
            'Only one warehouse assigned by one facility',
        ),
    ]

class Instance3PL(models.Model):
    _name = 'instance.3pl'
    _description = '3PL Instance'

    name = fields.Char(string='Instance Name', required=True)
    user_login_id = fields.Char(string='User Login ID', required=True)
    username = fields.Char(string='Username', required=True)
    password = fields.Char(string='Password', required=True)
    access_token = fields.Char(string='Access Token')
    customerId = fields.Integer(string="Customer ID")
    customerName = fields.Char(string="Customer Name")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    facilities_ids = fields.One2many('facilities.3pl', 'instance_3pl_id', string='Facilities')
    carriers_ids = fields.One2many('carriers.3pl', 'instance_3pl_id', string='Carriers')
    measure_type_ids = fields.One2many('measure.types', 'instance_3pl_id', string='Measure Types')

    _sql_constraints = [
        ('instance_name_uniq', 'unique(name)', 'Instance name must be unique.')
    ]

    def fetch_customers(self):
        url = "https://secure-wms.com/customers"
        headers = {
            'Accept-Language': 'en-US,en;q=0.8',
            'Host': 'secure-wms.com',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/hal+json'
            }
        headers['Authorization'] = 'Bearer ' + str(self.access_token)
        response = requests.request('GET', url, headers=headers, data={})
        if response.status_code == 200:
            response = json.loads(response.text)
            print(response)
            try:
                customerId = response.get('_embedded').get('http://api.3plCentral.com/rels/customers/customer')[0].get('readOnly').get('customerId')
                self.customerId = customerId
                companyName = response.get('_embedded').get('http://api.3plCentral.com/rels/customers/customer')[0].get('companyInfo').get('companyName')
                self.customerName = companyName
                #Facilities
                facilities = response.get('_embedded').get('http://api.3plCentral.com/rels/customers/customer')[0].get('facilities')
                print(facilities)
                if self.facilities_ids:
                    self.facilities_ids = [(5,0,0)]
                for facility in facilities:
                    self.env['facilities.3pl'].create({
                        'name': facility.get('name'),
                        'facilityId' : facility.get('id'),
                        'instance_3pl_id' : self.id
                    })
            except:
                raise UserError("Can not connect 3PL Central server.")

    def fetch_unit_of_measurements(self):
        url = "https://secure-wms.com/properties/unitofmeasuretypes"
        headers = {'Accept-Language': 'en-US,en;q=0.8', 'Host': 'secure-wms.com',
                   'Content-Type': 'application/json; charset=utf-8', 'Accept': 'application/hal+json',
                   'Authorization': 'Bearer ' + str(self.access_token)}
        response = requests.request('GET', url, headers=headers, data={})
        if response.status_code == 200:
            response = json.loads(response.text)
            try:
                measurements = response.get('_embedded').get('http://api.3plCentral.com/rels/properties/unitofmeasuretype')
                if self.measure_type_ids:
                    self.measure_type_ids = [(5, 0, 0)]
                for unit in measurements:
                    value = {'name': unit.get('name'),
                             'instance_3pl_id': self.id
                             }
                    self.env['measure.types'].create(value)
            except Exception as e:
                raise UserError(e)

    def fetch_carriers(self):
        #Carriers
        url = "https://secure-wms.com/properties/carriers"
        headers = {
            'Accept-Language': 'en-US,en;q=0.8',
            'Host': 'secure-wms.com',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/hal+json'
            }
        headers['Authorization'] = 'Bearer ' + str(self.access_token)
        response = requests.request('GET', url, headers=headers, data={})
        if response.status_code == 200:
            response = json.loads(response.text)
            try:
                carriers = response.get('_embedded').get('http://api.3plCentral.com/rels/properties/carrier')
                if self.carriers_ids:
                    self.carriers_ids = [(5,0,0)]
                for carrier in carriers:
                    service_ids = []
                    value = { 'name': carrier.get('name'),
                                'instance_3pl_id' : self.id
                            }
                    for service in carrier.get('shipmentServices'):
                        temp = {'name': service.get('description'),
                                'code': service.get('code'), 
                                'shipEngineId': service.get('shipEngineId')
                            }
                        service_ids.append((0, 0, temp))
                    if len(service_ids) > 0:
                        value['service_ids'] = service_ids
                    self.env['carriers.3pl'].create(value)
            except:
                raise UserError("Can not connect 3PL Central server.")

    def action_connect(self):
        self.fetch_customers()
        self.fetch_carriers()
        self.fetch_unit_of_measurements()

    def upsert_access_token(self):
        get_access_token_url = 'https://secure-wms.com/AuthServer/api/Token'
        payload = json.dumps({
                "grant_type": "client_credentials",
                "user_login": self.user_login_id,
            })
        headers = {
            'Host': 'secure-wms.com',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept-Language': 'en-US,en;q=0.8'
            }

        response = requests.request("POST", get_access_token_url, headers=headers, auth=HTTPBasicAuth(self.username, self.password), data=payload)
        if response.status_code == 200:
            response = json.loads(response.text)
            self.access_token = response.get('access_token')
        else:
            raise UserError(response.text)
            
    def refresh_access_token(self):
        to_refresh = self.env['instance.3pl'].search([])
        if not to_refresh:
            return
        for instance in to_refresh:
            instance.upsert_access_token()

    def map_products(self):
        pgsiz = 10
        url = "https://secure-wms.com/customers/{}/items?pgsiz={}".format(self.customerId, pgsiz)
        payload = {}
        headers = {
            'Host': 'secure-wms.com',
            'Content-Type': 'application/json',
            'Accept': 'application/hal+json',
            'Authorization': 'Bearer ' + str(self.access_token)
        }
        next_page = True
        while next_page:
            response = requests.request("GET", url, headers=headers, data=payload)
            if response.status_code == 200:
                res = json.loads(response.text)
                next_page = res.get('_links').get('next', False)
                if next_page:
                    next_page = True
                    url = 'https://secure-wms.com' + res.get('_links').get('next').get('href')
                response_dict = json.loads(response.text).get('_embedded').get('http://api.3plCentral.com/rels/customers/item')
                print(response_dict)
                for product in response_dict:
                    prod_res = self.env['product.product'].search([('default_code', '=', product['sku'])])
                    if prod_res:
                        prod_res.product_3pl_id = product['itemId']
                    else:
                        _logger.info('Product does not exist in Odoo. Product SKU: {}'.format(product['sku']))
            else:
                _logger.info(response.text)
                raise UserError(response.text)