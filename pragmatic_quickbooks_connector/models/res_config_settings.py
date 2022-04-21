from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'qbo.config.settings'
    _description = 'ResConfigSettings'

    update_customer_export = fields.Boolean('Update Customer While Export', default=True)
    update_customer_import = fields.Boolean('Update Customer While Import', default=True)

    update_vendor_export = fields.Boolean('Update Vendor While Export', default=True)
    update_vendor_import = fields.Boolean('Update Vendor While Import', default=True)

    update_product_export = fields.Boolean('Update Product While Export', default=True)
    update_product_import = fields.Boolean('Update Product While Import', default=True)

    update_account_import = fields.Boolean('Update Account While Import', default=False)
    update_account_export = fields.Boolean('Update Account While Export', default=False)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            update_customer_export=self.env['ir.config_parameter'].sudo().get_param('pragmatic_quickbooks_connector.update_customer_export'),
            update_customer_import=self.env['ir.config_parameter'].sudo().get_param('pragmatic_quickbooks_connector.update_customer_import'),
            update_vendor_export=self.env['ir.config_parameter'].sudo().get_param('pragmatic_quickbooks_connector.update_vendor_export'),
            update_vendor_import= self.env['ir.config_parameter'].sudo().get_param('pragmatic_quickbooks_connector.update_vendor_import'),
            update_product_export= self.env['ir.config_parameter'].sudo().get_param('pragmatic_quickbooks_connector.update_product_export'),
            update_product_import= self.env['ir.config_parameter'].sudo().get_param('pragmatic_quickbooks_connector.update_product_import'),
            update_account_export=self.env['ir.config_parameter'].sudo().get_param(
                'pragmatic_quickbooks_connector.update_account_export'),
            update_account_import=self.env['ir.config_parameter'].sudo().get_param(
                'pragmatic_quickbooks_connector.update_account_import'),

        )
        return res

    # @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()

        self.env['ir.config_parameter'].sudo().set_param('pragmatic_quickbooks_connector.update_customer_export', self.update_customer_export)
        self.env['ir.config_parameter'].sudo().set_param('pragmatic_quickbooks_connector.update_customer_import', self.update_customer_import)

        self.env['ir.config_parameter'].sudo().set_param('pragmatic_quickbooks_connector.update_vendor_export',self.update_vendor_export)
        self.env['ir.config_parameter'].sudo().set_param('pragmatic_quickbooks_connector.update_vendor_import',self.update_vendor_import)

        self.env['ir.config_parameter'].sudo().set_param('pragmatic_quickbooks_connector.update_product_export',self.update_product_export)
        self.env['ir.config_parameter'].sudo().set_param('pragmatic_quickbooks_connector.update_product_import',self.update_product_import)

        self.env['ir.config_parameter'].sudo().set_param('pragmatic_quickbooks_connector.update_account_export',
                                                     self.update_account_export)
        self.env['ir.config_parameter'].sudo().set_param('pragmatic_quickbooks_connector.update_account_import',
                                                     self.update_account_import)

