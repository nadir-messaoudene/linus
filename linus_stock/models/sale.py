from odoo import _, api, fields, models


class SaleOrderLineInherit(models.Model):
    _inherit = "sale.order.line"

    @api.depends(
        'product_id', 'customer_lead', 'product_uom_qty', 'product_uom', 'order_id.commitment_date',
        'move_ids', 'move_ids.forecast_expected_date', 'move_ids.forecast_availability')
    def _compute_qty_at_date(self):
        self = self.with_context(website_id=True)
        super(SaleOrderLineInherit, self)._compute_qty_at_date()