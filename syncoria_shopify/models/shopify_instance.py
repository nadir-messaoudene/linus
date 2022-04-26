# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import pprint
from odoo import models, fields, api, _
from odoo.http import request
import requests
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)
class ModelName(models.Model):
    _inherit = 'marketplace.instance'

    marketplace_app_id = fields.Integer(string='App ID',default=0)
    marketplace_instance_type = fields.Selection(selection_add=[('shopify', 'Shopify')], default='shopify')
    marketplace_api_key = fields.Char(string='API key', default='5302cfad84dc491cbbd6e7b9f549b750')
    marketplace_api_password = fields.Char(string='Password', default='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')
    marketplace_secret_key = fields.Char(string='Secret Key', default='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')
    marketplace_host = fields.Char(string='Host', default='faire-child-makewear.myshopify.com/')
    marketplace_webhook = fields.Boolean(
        string='Use Webhook?',
    )
    
    @api.onchange('marketplace_host')
    def _onchange_marketplace_host(self):
        if self.marketplace_host and 'https://' in str(self.marketplace_host):
            self.marketplace_host = self.marketplace_host.replace('https://','')

    
    marketplace_country_id = fields.Many2one(
        string='Country',
        comodel_name='res.country',
        ondelete='restrict',
    )
    marketplace_image_url = fields.Boolean(string='Is Image URL?',)

    marketplace_state = fields.Selection([
        ('draft', 'Not Confirmed'), 
        ('confirm', 'Confirmed')], 
        default='draft', string='State')
    marketplace_is_shopify = fields.Boolean(
        compute='_compute_is_shopify' )
    
    @api.depends('marketplace_instance_type')
    def _compute_is_shopify(self):
        for record in self:
            record.marketplace_is_shopify = False
            if record.marketplace_instance_type == 'shopify':
                record.marketplace_is_shopify = True

    
    marketplace_fetch_quantity = fields.Boolean(
        string='Update Product Quantity?',
    )
    marketplace_api_version = fields.Char(
        string='Api Version',
        default="2021-01"
    )
    # marketplace_api_version = fields.Selection(
    #     string='Api Version',
    #     selection=[('valor1', 'valor1'), ('valor2', 'valor2')]
    # )
    marketplace_journal_id  = fields.Many2one(
        string='Account Journal',
        comodel_name='account.journal',
        ondelete='restrict',
        required=True,
    )
    marketplace_payment_journal_id  = fields.Many2one(
        string='Payment Journal',
        comodel_name='account.journal',
        ondelete='restrict',
        required=True,
    )
    marketplace_refund_journal_id = fields.Many2one(
        string='Refund Journal',
        comodel_name='account.journal',
        ondelete='restrict'
    )
    marketplace_inbound_method_id  = fields.Many2one(
        string='Inbound Payment Method',
        comodel_name='account.payment.method',
        ondelete='restrict',
        required=True,
        domain=[('payment_type','=','inbound')]
    )
    marketplace_outbound_method_id  = fields.Many2one(
        string='Outbound Payment Method',
        comodel_name='account.payment.method',
        ondelete='restrict',
        required=True,
        domain=[('payment_type','=','outbound')]
    )

    debit_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Debit Account',
        store=True, readonly=False,
        # domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
        check_company=True)#	Current Assets
    credit_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Credit Account',
        store=True, readonly=False,
        domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
        check_company=True)#receivable


    ##############################################################################################################
    compute_pricelist_price = fields.Boolean(default=True)
    ##############################################################################################################

    # destination_account_id = fields.Many2one(
    #     comodel_name='account.account',
    #     string='Destination Account',
    #     store=True, readonly=False,
    #     compute='_compute_destination_account_id',
    #     domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
    #     check_company=True)
    
    # @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer')
    # def _compute_destination_account_id(self):
    #     self.destination_account_id = False
    #     for pay in self:
    #         if pay.is_internal_transfer:
    #             pay.destination_account_id = pay.journal_id.company_id.transfer_account_id
    #         elif pay.partner_type == 'customer':
    #             # Receive money from invoice or send money to refund it.
    #             if pay.partner_id:
    #                 pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_receivable_id
    #             else:
    #                 pay.destination_account_id = self.env['account.account'].search([
    #                     ('company_id', '=', pay.company_id.id),
    #                     ('internal_type', '=', 'receivable'),
    #                     ('deprecated', '=', False),
    #                 ], limit=1)
    #         elif pay.partner_type == 'supplier':
    #             # Send money to pay a bill or receive money to refund it.
    #             if pay.partner_id:
    #                 pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
    #             else:
    #                 pay.destination_account_id = self.env['account.account'].search([
    #                     ('company_id', '=', pay.company_id.id),
    #                     ('internal_type', '=', 'payable'),
    #                     ('deprecated', '=', False),
    #                 ], limit=1)



    
    def action_check_acess(self):
        url = self.marketplace_host + "/admin/oauth/access_scopes.json"
        access,next_link = self.env['marketplace.connector'].shopify_api_call(
            headers={'X-Shopify-Access-Token': self.marketplace_api_password},
            url=url,
            type='GET')
        if access.get('access_scopes'):
            msg =_("Store Acess Connection Successfull for Marketplace-%s" %(self.name))
            if self.marketplace_state != 'confirm':
                self.write({'marketplace_state' : 'confirm'})
            
        else:
            msg =_("Store Acess Connection Failed for Marketplace-%s" %(self.name))
        _logger.info(msg)
        self.message_post(body=msg)

    
    def action_cancel_state(self):
        msg =_("Store Acess Connection Disconnected for Marketplace-%s" %(self.name))
        self.write({'marketplace_state' : 'draft'})
        self.message_post(body=msg)
    

    ###########################################################################################
    ################################WEBHOOK####################################################
    ###########################################################################################

    def action_activate_webhook(self):
        _logger.info("action_activate_webhook===>>>>")
        url = self.marketplace_host + "admin/api/%s/webhooks.json" %(self.marketplace_api_version)
        access,next_link = self.env['marketplace.connector'].shopify_api_call(
            headers={'X-Shopify-Access-Token': self.marketplace_api_password},
            url=url,
            type='GET')

        if access.get('webhooks'):
            msg =_("Webhooks for Marketplace-%s" %(self.name))
            topics = ["orders/create"]

            for topic in topics:
                """WEBHOOKS FOR SHOPIFY"""
                icp_sudo = self.env['ir.config_parameter'].sudo()
                base_url =  icp_sudo.get_param('web.base.url')    
                _logger.info("base_url ===>>>> %s", base_url)   
                data = {
                    "webhook": {
                        "topic": "orders/create",
                        "address": base_url,
                        "format": "json"
                    }
                }

                _logger.info("data ===>>>> %s", data)
                webhooks,next_link = self.env['marketplace.connector'].shopify_api_call(
                    headers={'X-Shopify-Access-Token': self.marketplace_api_password,
                                'Content-Type': 'application/json'
                    },
                    url=url,
                    data=data,
                    type='POST')


                _logger.info("webhooks ===>>>>%s", webhooks)

                if webhooks.get('errors'):
                    raise UserError(_("Error-%s", str(webhooks.get('errors'))))
                else:
                    msg =_("Webhooks Successfully Created for-%s" %(self.name))
  
        else:
            msg =_("Webhooks Failed for Marketplace-%s" %(self.name))
        _logger.info(msg)

        
        # self.message_post(body=msg)


    def action_remove_webhook(self):
        res = self.shopify_webhook_request('fetch')
        _logger.info("res===>>>>%s", res)
        res = res.json()
        wbhk_ids = [wbhk['id'] for wbhk in res.get('webhooks')]
        for wbhk in wbhk_ids:
            headers = {'X-Shopify-Access-Token': self.marketplace_api_password} 
            version = self.marketplace_api_version or '2021-04'
            url = 'https://' + self.marketplace_host if 'https://' not in self.marketplace_host or 'http://' not in self.marketplace_host else self.marketplace_host
            url += '/admin/api/%s/webhooks/%s.json' %(version,wbhk)
            response = requests.request(headers=headers,
                                        url=url,
                                        method='DELETE')
            _logger.info("url===>>>%s", url)
            _logger.info("response===>>>%s", response)
            if response.status_code == 200:
                _logger.info("response.text===>>>%s", response.text)
                _logger.info("Webhook has been successfully deleted!")


    def shopify_webhook_request(self, r_type):
        type_req = 'POST' if r_type == 'create' else 'PUT'
        type_req = 'PUT' if r_type == 'update' else type_req
        type_req = 'GET' if r_type == 'fetch' else type_req
        type_req = 'DEL' if r_type == 'delete' else type_req

        version = self.marketplace_api_version or '2021-04'
        url = 'https://' + self.marketplace_host if 'https://' not in self.marketplace_host or 'http://' not in self.marketplace_host else self.marketplace_host
        url += '/admin/api/%s/webhooks.json' % version
        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.marketplace_api_password} 
        data = {}
        response = requests.request(headers=headers,
                                    data=data,
                                    url=url,
                                    method=type_req)
        _logger.info("headers===>>>%s", headers)
        _logger.info("data===>>>%s", data)
        _logger.info("response===>>>%s", response)
        status_code = response.status_code
        res =  response.json()
        res['status_code'] = status_code
        return response



    color = fields.Integer(default=10)
    marketplace_count_orders = fields.Integer('Order Count', compute='_compute_count_of_records')
    marketplace_count_products = fields.Integer('Product Count', compute='_compute_count_of_records')
    marketplace_count_customers = fields.Integer('Customer Count', compute='_compute_count_of_records')
    marketplace_database_name = fields.Char('Database Name', compute='_compute_count_of_records')
    marketplace_current_user = fields.Char('Current User', compute='_compute_count_of_records')


    def _compute_count_of_records(self):
        """
        Count of Orders, Products, Customers for dashboard

        :return: None
        """
        for rec in self:
            search_query = [('shopify_instance_id', '=', rec.id), ('shopify_id', '!=', False)]
            rec.marketplace_database_name = request.session.db
            rec.marketplace_current_user = self.env.user.id
            rec.marketplace_count_orders = rec.env['sale.order'].search_count(search_query)
            rec.marketplace_count_products = rec.env['product.template'].search_count(search_query)
            rec.marketplace_count_customers = rec.env['res.partner'].search_count(search_query)

    def open_form_action(self):
        """
        Open the Operation Form View in the wizard

        :return: The form view
        """
        view = self.env.ref('syncoria_shopify.view_instance_form_shopify')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shopify Operations',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_model': 'marketplace.instance',
            'view_mode': 'form',
            # 'context': {'default_marketplace_instances': [(4, 0, [self.id])], 'default_woo_instance': True},
            'target': 'new',
        }

    def shopify_open_marketplace_orders(self):
        """
        Open the view regarding the Sales Order with respective to Instance

        :return: The view
        """
        action = self.env.ref('syncoria_shopify.shopify_order_action').read()[0]
        action['domain'] = [('shopify_instance_id', '=', self.id)]
        return action

    def shopify_open_marketplace_products(self):
        """
        Open the view regarding the Products with respective to Instance

        :return: The view
        """
        action = self.env.ref('syncoria_shopify.shopify_product_action').read()[0]
        action['domain'] = [('shopify_instance_id', '=', self.id)]
        return action


    def shopify_open_marketplace_customers(self):
        """
        Open the view regarding the Customers with respective to Instance

        :return: The view
        """
        action = self.env.ref('syncoria_shopify.res_partner_action_customer').read()[0]
        action['domain'] = [('shopify_instance_id', '=', self.id)]
        return action

    def shopify_open_marketplace_configuration(self):
        """
        Open the Shopify Configuration wizard

        :return: The form view
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shopify Operations',
            'view': 'form',
            'res_id': self.id,
            'res_model': 'marketplace.instance',
            'view_mode': 'form',
        }

    def shopify_open_instance_logs(self):
        """
        Redirect to the Instance log form view

        :return: The tree view
        """
        action = self.env.ref('syncoria_shopify.action_shopify_marketplace_logging').read()[0]
        action['domain'] = [('shopify_instance_id', '=', self.id)]
        return action

