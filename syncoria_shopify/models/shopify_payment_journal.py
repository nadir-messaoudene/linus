from odoo import models, api, fields, tools, exceptions, _
import logging
logger = logging.getLogger(__name__)


class ShopifyPaymentJournal(models.Model):
    _name = 'shopify.payment.journal'

    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID", required=True)
    tag_id = fields.Many2one("crm.tag", string="Tag", required=True)
    journal_id = fields.Many2one("account.journal", string="Payment Journal", required=True)
