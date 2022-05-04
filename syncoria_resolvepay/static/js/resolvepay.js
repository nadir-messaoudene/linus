//odoo.define('syncoria_resolvepay.resolvepay_payment_footer_inherit', function (require) {
//    'use strict';
//    var Widget = require('web.Widget');
//    var core = require('web.core');
//
//    var Checkout = Widget.extend({
//        events: {
//            'click #resolvepay_direct_checkout': '_onClick',
//        },
//        init: function (parent, value) {
//            this._super(parent);
//        },
//        _onClick: function () {
//            console.log('_onClick')
//        },
//    });
//    core.action_registry.add("resolvepay_checkout", Checkout);
//    return Checkout;
//});
(function () {
  // some code here
  let a = 1;
  var elem = document.getElementById('resolvepay_direct_checkout');
  $().ready(function() {
    $('#resolvepay_direct_checkout').click(function() {
        resolve.checkout({
          sandbox: true, // INCLUDE ONLY IF USING SANDBOX ENVIRONMENT (default is production)
          modal: true,
          merchant: {
            id:          'linusbike',
            success_url: 'https://www.merchantsite.com/confirm',
            cancel_url:  'https://www.merchantsite.com/cancel',
          },
          customer: {
            first_name: 'First',
            last_name:  'Last',
            name:       'First Last', // (optional) full name
            phone:      '',
            email:      '',
          },
          shipping: {
            name:            'First Last',
            company_name:    'Company Name', // optional
            phone:           '4153334567',
            address_line1:   '633 Folsom St',
            address_line2:   'FL 7', // optional
            address_city:    'San Francisco',
            address_state:   'CA',
            address_postal:  '94017',
            address_country: 'US',
          },
          billing: {
            name:            '',
            company_name:    '',
            phone:           '',
            address_line1:   '',
            address_line2:   '',
            address_city:    '',
            address_state:   '',
            address_postal:  '',
            address_country: '',
          },
          items: [{
            name:       'Product Name',
            sku:        'ABC-123',
            unit_price: 19.99,
            quantity:   3,
          }],

          order_number: 'ORDER_NUMBER', // (optional) merchant internal order id
          po_number:    '', // (optional) customer's purchase order #

          shipping_amount: 10.00,
          tax_amount:       5.00,
          total_amount:    74.97,
        });
    });
  });
})();
