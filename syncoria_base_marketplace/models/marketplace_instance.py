# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _


class MarketplaceInstance(models.Model):
    _inherit = ['mail.thread','mail.activity.mixin',]
    _name = 'marketplace.instance'
    _description = 'Marketplace Instance'
    _order = "id desc"
    
    marketplace_instance_type = fields.Selection(
        string='Instance Type',
        selection=[]
    )
    name = fields.Char(string='Instance Name', required=True,
                       copy=False, index=True, default=lambda self: _('New'))
    # Options
    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        ondelete='restrict',
        required=True
    )
    

    @api.onchange('company_id')
    def _onchange_company_id(self):
        res = {'domain': {'warehouse_id': [
            ('company_id', 'in', self.company_id.ids)]}}
        return res

    @api.onchange('company_id')
    def _onchange_company_id_2(self):
        res = {'domain':{'fiscal_position_id':[('company_id','in',self.company_id.ids)]}}
        return res

    @api.onchange('company_id')
    def _onchange_company_id_3(self):
        res = {'domain':{'user_id':[('company_id','in',self.company_id.ids)]}}
        return res

    warehouse_id = fields.Many2one(
        string='Warehouse',
        comodel_name='stock.warehouse',
        ondelete='restrict',
        required=True
    )
    langauge_id = fields.Many2one(
        string='Language',
        comodel_name='res.lang',
        ondelete='restrict',
        required=True
    )

    fiscal_position_id = fields.Many2one(
        string='Fiscal Position',
        comodel_name='account.fiscal.position',
        ondelete='restrict',
        # required=True
    )
    user_id = fields.Many2one(
        string='Salesperson',
        comodel_name='res.users',
        ondelete='restrict',
        required=True
    )

    # Product Bulk Export Operations

    set_price = fields.Boolean(
        string='Set Price ?',
    )
    set_stock = fields.Boolean(
        string='Set Stock?',
    )
    publish_in_website = fields.Boolean(
        string='Publish in Website?',
    )
    set_image = fields.Boolean(
        string='Set Image?',
    )

    # Product Bulk Sync Operations
    sync_product_image = fields.Boolean(
        string='Sync Images?', 
        default=True,
    )
    sync_price = fields.Boolean(
        string='Import/Sync Price?',
        default=True,
    )
    #For Channel Advisor
    sync_qty = fields.Boolean(
        string='Sync Quantity?',
        default=True,
    )
    import_price = fields.Boolean(
        string='Import Price?',
        default=True,
    )
    import_product_image = fields.Boolean(
        string='Import Product Image?',
        default=True,
    )
    import_qty = fields.Boolean(
        string='Import Product Quantity?',
        default=True,
    )


    # Product Informations
    discount_product_id = fields.Boolean(
        string='Discount',
    )
    calculate_discount = fields.Boolean(
        string='Calculate Discount Tax',
    )
    default_invoice_policy = fields.Selection(
        string='Invoicing Policy',
        selection=[('order', 'Ordered Quantities'),
                   ('delivery', 'Delivered Quantities')],
        default='order',
    )
    duplicate_barcode_check = fields.Boolean()
       
    @api.onchange('default_invoice_policy')
    def _onchange_invoice_policy(self):
        print("_onchange_invoice_policy")
        print(self.default_invoice_policy)
        ICPSudo = self.env['ir.config_parameter'].sudo()
        def_invoice_policy =  ICPSudo.get_param('sales.default_invoice_policy')
        print("Before: ", def_invoice_policy)
        ICPSudo.set_param('sales.default_invoice_policy', self.default_invoice_policy)
        def_invoice_policy =  ICPSudo.get_param('sales.default_invoice_policy')
        print("After: ", def_invoice_policy)

    # Payment Informations
    pricelist_id = fields.Many2one(
        string='Pricelist',
        comodel_name='product.pricelist',
        ondelete='restrict',
        required=True
    )
    payment_term_id = fields.Many2one(
        string='Payment Terms',
        comodel_name='account.payment.term',
        ondelete='restrict',
        required=True,
    )
    marketplace_journal_id = fields.Many2one(
        string='Journal',
        comodel_name='account.journal',
        ondelete='restrict',
        required=True,
    )
    
    
    # Order Informations
    #Auto Order Import
    ao_import = fields.Boolean(string='Auto Order Import?')
    ao_import_interval = fields.Integer(default=1, help="Repeat every x.")
    ao_import_interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months')], string='Interval Type', default='hours')
    
    ao_import_nextcall = fields.Datetime(
        string='Next Import Execution Date', 
        default=fields.Datetime.now, 
        help="Next planned execution date for this job.")
    ao_import_user_id = fields.Many2one('res.users', 
        string='Scheduler User', 
        default=lambda self: self.env.user)

    #Auto Order Update
    ao_update = fields.Boolean(string='Auto Order Update?')
    ao_update_interval = fields.Integer(default=1, help="Repeat every x.")
    ao_update_interval_type = fields.Selection([('minutes', 'Minutes'),
                                      ('hours', 'Hours'),
                                      ('days', 'Days'),
                                      ('weeks', 'Weeks'),
                                      ('months', 'Months')], string='Interval Unit', default='hours')
    ao_update_nextcall = fields.Datetime(
        string='Next Execution Date', default=fields.Datetime.now, help="Next planned execution date for this job.")
    ao_update_user_id = fields.Many2one(
        'res.users', string='User', 
        default=lambda self: self.env.user)

    order_tracking_ref = fields.Boolean(
        string='One order can have multiple Tracking Number?',
    )
    order_prefix = fields.Char()

    auto_close_order = fields.Boolean(
        string='Auto Closed Order',
    )
    auto_create_product = fields.Boolean(
        string='Auto Create Product if not found?',default= True
    )
    notify_customer = fields.Boolean(
        string='Notify Customer about Update Order Status',
    )

    sales_team_id = fields.Many2one(
        string='Sales Team',
        comodel_name='crm.team',
        ondelete='restrict',
    )
    auto_create_invoice = fields.Boolean(
        string='Auto Create Invoice?',
        default=True,
    )
    auto_create_fulfilment = fields.Boolean(
        string='Auto Create Fulfilment?',
        default=False,
    )
    analytic_account_id = fields.Many2one(
        string='Analytic Account',
        comodel_name='account.analytic.account',
        ondelete='restrict',
    )
    

    # Stock Information
    stock_auto_export = fields.Boolean(
        string='Stock Auto Export?',
    )

    stock_fields = fields.Selection(
        string='Stock Field',
        selection=[('onhand', 'Quantity on Hand (product.product)'),
                   ('Forecast', 'Forecast Quantity (product.product)')]
    )

    # @api.onchange('auto_create_product')
    # def _onchange_auto_create_product(self):
    #     self.auto_create_product = False
    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'marketplace.instance') or _('New')
        self._update_crons(vals)
        result = super(MarketplaceInstance, self).create(vals)
        self._update_sale_sequence(vals)
        return result


    def write(self, vals):
        self._update_crons(vals)
        result = super(MarketplaceInstance, self).write(vals)
        self._update_sale_sequence(vals)
        return result

    def _update_sale_sequence(self,vals):
        if vals.get('order_prefix'):
            Sequence = self.env['ir.sequence'].sudo()
            seq_id = Sequence.search([('code', '=', 'sale.order')])
            seq_id.sudo().write({'prefix':vals.get('order_prefix')})


    def _update_crons(self,vals):
        print(vals)
        Cron = self.env['ir.cron'].sudo()

        switcher={
                'ao_import':'active',
                'ao_import_user_id':'user_id',
                'ao_import_interval':'interval_number',
                'ao_import_interval_type':'interval_type',
                'ao_import_nextcall':'nextcall',
             }

        ao_vals = {}
        ao_values = ['ao_import','ao_import_user_id','ao_import_interval','ao_import_interval_type','ao_import_nextcall']
        for key in ao_values:
            if vals.get(key):
                ao_vals[switcher.get(key)] = vals.get(key)
            if key == 'ao_import' and vals.get(key) == True:
                ao_vals.update({
                        'user_id':self.ao_import_user_id.id,
                        'interval_number':self.ao_import_interval,
                        'interval_type':self.ao_import_interval_type,
                        'nextcall':self.ao_import_nextcall,
                })
            if key == 'ao_import' and vals.get(key) == False:
                ao_vals.update({'active':vals.get(key)})

        if len(ao_vals) > 0:
            cron_id = Cron.search([('name','=','Shopify: Fetch Orders'),('active','in',(True,False))])
            cron_id.write(ao_vals)
            if vals.get('ao_import') == False:
                cron_id.write({'active':False})


        switcher={
                'ao_update':'active',
                'ao_update_user_id':'user_id',
                'ao_update_interval':'interval_number',
                'ao_update_interval_type':'interval_type',
                'ao_update_nextcall':'nextcall',
             }

        update_vals = {}
        update_values = ['ao_update', 'ao_update_user_id',
                         'ao_update_interval', 'ao_update_interval_type', 'ao_update_nextcall']
        for key in update_values:
            if vals.get(key):
                update_vals[switcher.get(key)] = vals.get(key)
            if key == 'ao_update' and vals.get(key) == True:
                update_vals.update({
                        'user_id':self.ao_update_user_id.id,
                        'interval_number':self.ao_update_interval,
                        'interval_type':self.ao_update_interval_type,
                        'nextcall':self.ao_update_nextcall,
                })
            if key == 'ao_update' and vals.get(key) == False:
                update_vals.update({'active':vals.get(key)})

        if len(update_vals) > 0:
            cron_id = Cron.search([('name','=','Shopify: Export Orders'),('active','in',(True,False))])
            cron_id.write(update_vals)

        if vals.get('discount_product_id'):
            # Does not work
            ICPSudo = self.env['ir.config_parameter'].sudo()
            discount = ICPSudo.get_param('sales.group_discount_per_so_line')
            print("BEFORE: ", discount)
            ICPSudo.set_param('sales.group_discount_per_so_line', vals.get('discount_product_id'))
            self._cr.commit()
            discount = ICPSudo.get_param('sales.group_discount_per_so_line')
            print("AFTER: ", discount)


    #################################################
    ###################WEBHOOKS######################
    #################################################
    marketplace_webhooks_ids = fields.One2many(
        string='Marketplace Webhooks',
        comodel_name='marketplace.webhooks',
        inverse_name='marketplace_instance_id',
    )