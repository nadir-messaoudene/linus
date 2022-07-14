# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet
import requests
import json
from odoo.tools.misc import format_date

class Location(models.Model):
    _inherit = 'stock.location'

    is_manual_validate = fields.Boolean("Is Manual Validate", default=False)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('push_3pl', 'Pushed to 3PL'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Push to 3PL: This transfer is integrated/pushed with/to 3PL.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")
    threeplId = fields.Integer(string="3PL ID", copy=False)
    container_ref = fields.Char(string="Container Reference",copy=False)
    warehouse_instruction = fields.Char(string="Warehouse Instruction",copy=False)
    carrier_instruction = fields.Char(string="Carrier Instruction",copy=False)

    carriers_3pl_id = fields.Many2one('carriers.3pl', 'Carrier', domain="[('instance_3pl_id', '=', 1)]")
    carrier_services_3pl_id = fields.Many2one('carrier.services.3pl', 'Service', domain="[('carrier_3pl_id', '=', carriers_3pl_id)]")
    ship_by_3pl = fields.Boolean("Ship by 3PL", compute="_compute_ship_by_3pl")

    def action_update_3pl_pickings(self):
        to_update = self.env['stock.picking'].search([('state', '=', 'push_3pl')])
        if not to_update:
            return
        for rec in to_update:
            rec.update_picking_from_3pl()

    @api.depends('picking_type_id')
    def _compute_ship_by_3pl(self):
        instance = self.env['instance.3pl'].search([], limit=1)
        for rec in self:
            rec.ship_by_3pl = False
            for facility in instance.facilities_ids:
                if facility.warehouse_id.id == rec.picking_type_id.warehouse_id.id:
                    rec.ship_by_3pl = True

    def get_3pl_warehouse_from_locations(self, location_obj):
        warehouse_ids = [location_obj.warehouse_id.id]
        instance = self.env['instance.3pl'].search([], limit=1)
        for facility in instance.facilities_ids:
            if facility.warehouse_id.id in warehouse_ids:
                return facility.facilityId
        return False

    def action_push_to_3pl(self):
        if self.state == 'draft':
            raise UserError('Can not export draft Transfer')
        if self.picking_type_id.code == 'outgoing':
            source_warehouse = self.get_3pl_warehouse_from_locations(self.location_id)
            if source_warehouse:
                # To Create 3PL Order
                self.export_picking_to_3pl(source_warehouse)
                self.state = 'push_3pl'
        elif self.picking_type_id.code == 'incoming':
            source_warehouse = self.get_3pl_warehouse_from_locations(self.location_dest_id)
            if source_warehouse:
                # To Create 3PL Receipt
                self.export_picking_to_3pl_purchase_order(source_warehouse)
                self.state = 'push_3pl'
        elif self.picking_type_id.code == 'internal' and self.location_dest_id.is_manual_validate:
            source_warehouse = self.get_3pl_warehouse_from_locations(self.location_id)
            if source_warehouse:
                # To Create 3PL Order
                self.export_picking_to_3pl(source_warehouse)
                self.state = 'push_3pl'

    def export_picking_to_3pl(self, source_warehouse):
        if not self.carrier_services_3pl_id:
            raise UserError("Please select 3PL Carrier and Service.")
        if not self.partner_id.street or not self.partner_id.city or not self.partner_id.state_id.code or not self.partner_id.zip or not self.partner_id.country_id.code:
            raise ValidationError("Please check shipping address.")
        print("export_picking_to_3pl")
        if self.state in ('waiting', 'confirmed', 'assigned'):
            instance = self.env['instance.3pl'].search([], limit=1)
            url = "https://secure-wms.com/orders"
            # orderItems
            orderItems = []
            # Make sure have done line(s)
            flag = False
            for line in self.move_line_ids_without_package:
                if line.qty_done:
                    flag = True
            if not flag:
                raise UserError("Please modify 'Done' quantity before pushing to 3PL.")
            # END Make sure have done line(s)
            for line in self.move_line_ids_without_package:
                if line.qty_done > 0:
                    orderItems.append(
                            {
                            "itemIdentifier": {
                                "sku": line.product_id.default_code
                            },
                            "qty": line.qty_done
                            }
                    )
            # END orderItems
            
            payload = json.dumps({
                "customerIdentifier": {
                    "id": instance.customerId
                },
                "facilityIdentifier": {
                    "id": source_warehouse
                },
                "referenceNum": self.name,
                "notes": self.warehouse_instruction if self.warehouse_instruction else "",
                "shippingNotes": self.carrier_instruction if self.carrier_instruction else "",
                "billingCode": "Prepaid",
                "routingInfo": {
                    "carrier": self.carrier_services_3pl_id.carrier_3pl_id.name,
                    "mode": self.carrier_services_3pl_id.code,
                    "account": self.carrier_services_3pl_id.carrier_3pl_id.account_number,
                },
                "shipTo": {
                    "companyName": self.partner_id.name,
                    "name": self.partner_id.name,
                    "address1": self.partner_id.street,
                    "address2": self.partner_id.street2 if self.partner_id.street2 else "",
                    "city": self.partner_id.city,
                    "state": self.partner_id.state_id.code,
                    "zip": self.partner_id.zip,
                    "country": self.partner_id.country_id.code
                },
                'soldTo': {
                    'sameAs': 0
                },
                "orderItems": orderItems
                })
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/hal+json',
                'Authorization': 'Bearer ' + str(instance.access_token)
                }
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 201:

                pickings_to_backorder = self._check_backorder()
                if pickings_to_backorder:
                    # START processing back order
                    moves_todo = self.mapped('move_lines').filtered(lambda move: move.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'] and move.quantity_done > 0)
                    backorder_moves_vals = []
                    for move in moves_todo:
                        # To know whether we need to create a backorder or not, round to the general product's
                        # decimal precision and not the product's UOM.
                        rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
                        if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
                            # Need to do some kind of conversion here
                            qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done,
                                                                           move.product_id.uom_id,
                                                                           rounding_method='HALF-UP')
                            new_move_vals = move._split(qty_split)
                            backorder_moves_vals += new_move_vals
                        move.move_line_ids.with_context(bypass_reservation_update=True).write({
                            'product_uom_qty': move.quantity_done,
                            'date': fields.Datetime.now(),
                        })
                    backorder_moves = self.env['stock.move'].create(backorder_moves_vals)
                    self._create_backorder_custom(moves_todo.ids)
                response = json.loads(response.text)
                self.threeplId = response.get('readOnly').get('orderId')
            else:
                raise UserError(response.text)
        else:
            raise UserError("Only Order in Waiting and Ready state can be pushed to 3PL.")

    def update_picking_from_3pl(self):
        for record in self:
            print("update_picking_from_3pl")
            instance = self.env['instance.3pl'].search([], limit=1)
            if record.picking_type_id.code == 'incoming':
                return
            if not record.threeplId:
                raise UserError("The transfer does not have 3PL ID (Maybe it hasn't been exported)")
            if not record.state == 'push_3pl':
                raise UserError("Only 'Push To 3PL' orders can be updated")
            url = "https://secure-wms.com/orders/{}".format(record.threeplId)

            headers = {
                'Host': 'secure-wms.com',
                'Accept-Language': 'en-US,en;q=0.8',
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/hal+json',
                'Authorization': 'Bearer ' + str(instance.access_token)
            }
            response = requests.request("GET", url, headers=headers, data={})
            print(response.status_code)
            if response.status_code == 200:
                response = json.loads(response.text)
                print(response)
                is_closed = response.get('readOnly').get('isClosed')
                status = response.get('readOnly').get('status')
                fully_allocated = response.get('readOnly').get('fullyAllocated')
                print(is_closed)
                print(status)
                # CANCEL ORDER
                if is_closed and status == 2:
                    if record.state == 'push_3pl':
                        record.action_cancel()
                # CLOSED ORDER
                if is_closed and status == 1 and fully_allocated:
                    tracking_number = response.get('routingInfo').get('trackingNumber')
                    record.carrier_tracking_ref = tracking_number
                    # Check if this picking is internal transfer and the dest location is manual validated
                    if record.picking_type_id.code == 'internal' and record.location_dest_id.is_manual_validate:
                        return
                    # Line 210 - 224: To Compare Qty Done between Odoo and 3PL, overwrite Odoo Qty if 3PL has less
                    items_dict = record.get_order_item_3pl(record.threeplId)
                    dict_item_to_create_backorder_lines = {}
                    for item in items_dict:
                        item_3pl_id = item.get('itemIdentifier').get('id')
                        item_qty = item.get('qty')
                        item_odoo_id = self.env['product.product'].search([('product_3pl_id', '=', item_3pl_id)])
                        if not item_odoo_id:
                            raise UserError('Can not find the product with 3pl id: ' + str(item_3pl_id))
                        res_item = record.move_line_ids_without_package.filtered(lambda l: l.product_id == item_odoo_id)
                        if not res_item:
                            raise UserError(
                                'Can not find move_line_ids_without_package with product_id: ' + str(item_odoo_id.id))
                        if res_item.qty_done != item_qty:
                            dict_item_to_create_backorder_lines[item_odoo_id.id] = res_item.qty_done - item_qty
                            res_item.write({'qty_done': item_qty})
                    res_dict = record.button_validate()
                    if type(res_dict) != bool:
                        self.env['stock.backorder.confirmation'].with_context(res_dict['context']).process()
                    sale_order = self.env['sale.order'].search([('name', '=', record.origin)])
                    if sale_order and sale_order.shopify_id:
                        record.create_shopify_fulfillment()
            else:
                raise UserError(response.text)

    def get_order_item_3pl(self, order_id):
        instance = self.env['instance.3pl'].search([], limit=1)
        url = "https://secure-wms.com/orders/{}/items".format(order_id)

        headers = {
            'Host': 'secure-wms.com',
            'Accept-Language': 'en-US,en;q=0.8',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/hal+json',
            'Authorization': 'Bearer ' + str(instance.access_token)
        }
        response = requests.request("GET", url, headers=headers, data={})
        if response.status_code == 200:
            response = json.loads(response.text)
            print(json.dumps(response, indent=2))
            return response.get('_embedded').get('http://api.3plCentral.com/rels/orders/item')
        else:
            raise UserError(response.text)

    def export_picking_to_3pl_purchase_order(self, source_warehouse):
        if self.state in ('waiting', 'confirmed', 'assigned'):
            instance = self.env['instance.3pl'].search([], limit=1)
            url = "https://secure-wms.com/inventory/receivers"
            orderItems = []
            for line in self.move_ids_without_package:
                if not line.product_id.default_code:
                    raise UserError('SKU on product must exist')
                orderItems.append(
                    {
                        "itemIdentifier": {
                            "sku": line.product_id.default_code
                        },
                        "qty": line.product_uom_qty,
                    }
                )
            payload = json.dumps({
                "customerIdentifier": {
                    "id": instance.customerId
                },
                "facilityIdentifier": {
                    "id": source_warehouse
                },
                "referenceNum": self.container_ref,
                "receiptAdviceNumber": self.name,
                "poNum": self.origin,
                "arrivalDate": str(self.scheduled_date),
                "expectedDate": str(self.scheduled_date),
                "notes": "",
                "shipTo": {
                    "sameAs": 0,
                    "companyName": self.partner_id.name,
                    "name": self.partner_id.name,
                    "address1": self.partner_id.street,
                    "address2": self.partner_id.street2,
                    "city": self.partner_id.city,
                    "state": self.partner_id.state_id.code,
                    "zip": self.partner_id.zip,
                    "country": self.partner_id.country_id.code
                },
                "_embedded": {
                    "http://api.3plCentral.com/rels/inventory/receiveritem": orderItems
                }
            })

            headers = {
                'Host': 'secure-wms.com',
                'Content-Type': 'application/hal+json; charset=utf-8',
                'Accept': 'application/hal+json',
                'Authorization': 'Bearer ' + str(instance.access_token)
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 201:
                # res_dict = self.button_validate()
                # if type(res_dict) != bool:
                #     self.env['stock.immediate.transfer'].with_context(res_dict['context']).process()
                response = json.loads(response.text)
                self.threeplId = response.get('readOnly').get('receiverId')
            else:
                raise UserError(response.text)
        else:
            raise UserError("Only Order in Waiting and Ready state can be pushed to 3PL.")

    def _create_backorder_custom(self, ids):
        backorders = self.env['stock.picking']
        bo_to_assign = self.env['stock.picking']
        for picking in self:
            moves_to_backorder = picking.move_lines.filtered(lambda x: x.id not in ids or x.quantity_done == 0)
            if moves_to_backorder:
                backorder_picking = picking.copy({
                    'name': '/',
                    'move_lines': [],
                    'move_line_ids': [],
                    'backorder_id': picking.id
                })
                picking.message_post(
                    body=_('The backorder <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created.') % (
                        backorder_picking.id, backorder_picking.name))
                moves_to_backorder.write({'picking_id': backorder_picking.id})
                moves_to_backorder.move_line_ids.package_level_id.write({'picking_id':backorder_picking.id})
                moves_to_backorder.mapped('move_line_ids').write({'picking_id': backorder_picking.id})
                backorders |= backorder_picking
                if backorder_picking.picking_type_id.reservation_method == 'at_confirm':
                    bo_to_assign |= backorder_picking
        if bo_to_assign:
            bo_to_assign.action_assign()
        return backorders

    # @api.depends('state', 'picking_type_code', 'scheduled_date', 'move_lines', 'move_lines.forecast_availability',
    #              'move_lines.forecast_expected_date')
    # def _compute_products_availability(self):
    #     pickings = self.filtered(lambda picking: picking.state in (
    #     'waiting', 'confirmed', 'assigned', 'push_3pl') and picking.picking_type_code == 'outgoing')
    #     pickings.products_availability_state = 'available'
    #     pickings.products_availability = _('Available')
    #     other_pickings = self - pickings
    #     other_pickings.products_availability = False
    #     other_pickings.products_availability_state = False
    #
    #     all_moves = pickings.move_lines
    #     # Force to prefetch more than 1000 by 1000
    #     all_moves._fields['forecast_availability'].compute_value(all_moves)
    #     for picking in pickings:
    #         # In case of draft the behavior of forecast_availability is different : if forecast_availability < 0 then there is a issue else not.
    #         if any(float_compare(move.forecast_availability, 0 if move.state == 'draft' else move.product_qty,
    #                              precision_rounding=move.product_id.uom_id.rounding) == -1 for move in
    #                picking.move_lines):
    #             picking.products_availability = _('Not Available')
    #             picking.products_availability_state = 'late'
    #         else:
    #             forecast_date = max(
    #                 picking.move_lines.filtered('forecast_expected_date').mapped('forecast_expected_date'),
    #                 default=False)
    #             if forecast_date:
    #                 picking.products_availability = _('Exp %s', format_date(self.env, forecast_date))
    #                 picking.products_availability_state = 'late' if picking.scheduled_date and picking.scheduled_date < forecast_date else 'expected'