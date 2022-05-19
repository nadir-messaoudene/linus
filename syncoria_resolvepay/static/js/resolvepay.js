//odoo.define('syncoria_resolvepay.payment_checkout', require => {
//    'use strict';
//
//    var publicWidget = require('web.public.widget');
//
//    const core = require("web.core");
//    const ajax = require("web.ajax");
//
//    const checkoutForm = require("payment.checkout_form");
//    const manageForm = require("payment.manage_form");
//    const Dialog = require("web.Dialog");
//
//    const resolvePayCheckoutMixin = {
//      /**
//         *
//         * @override method from payment.payment_form_mixin
//         * @private
//         * @param {string} provider - The provider of the payment option's acquirer
//         * @param {number} paymentOptionId - The id of the payment option handling the transaction
//         * @param {string} flow - The online payment flow of the transaction
//         * @return {Promise}
//         */
//       _processPayment: function(provider, paymentOptionId, flow) {
//        console.log("--------------------------------------");
//        console.log("Resolve Pay ==>>>_processPayment ===>>>>");
//        console.log("provider ===>>>>", provider);
//        console.log("paymentOptionId ===>>>>", paymentOptionId);
//        console.log("flow ===>>>>", flow);
//        console.log("--------------------------------------");
//
//        if (paymentOptionId != 15) {
//          return this._super(...arguments);
//        }
//
//        if (paymentOptionId == 15) {
//          return this._rpc({
//                route: "/shop/resolvepay/get_sale_order",
//            })
//            .then((orderInfo) => {
//                if (!orderInfo) {
//                    window.location.replace('/resolvepay/success');
//                } else {
//                    resolve.checkout({
//                    sandbox: true, // INCLUDE ONLY IF USING SANDBOX ENVIRONMENT (default is production)
//                    merchant: {
//                      id:          'linusbike',
//                      success_url: window.location.origin + '/resolvepay/confirm',
//                      cancel_url:  window.location.origin + '/resolvepay/cancel'
//                    },
//                    customer: {
//                      ...orderInfo.customer
//                    },
//                    shipping: {
//                      ...orderInfo.shipping
//                    },
//                    billing: {
//                      ...orderInfo.billing
//                    },
//                    items: orderInfo.items,
//
//                    order_number: orderInfo.order_number, // (optional) merchant order number
//                    po_number:    '', // (optional) buyer purchase order number if required
//
//                    shipping_amount:  0.00,
//                    tax_amount:       orderInfo.tax_amount,
//                    total_amount:     orderInfo.total_amount,
//                    });
//                }
//            });
//          }
//      },
//    }
//    checkoutForm.include(resolvePayCheckoutMixin);
//    manageForm.include(resolvePayCheckoutMixin);
//});
//
//
//
//
//
//
//
//
//
//
//
//
//
//
//
//
//
//
//
//
////     publicWidget.registry.ResolvePayButton = publicWidget.Widget.extend({
////         selector: '#resolvepay_direct_checkout',
////         events: {
////             'click': '_onClick',
////         },
//
////         _onClick: function () {
////             return this._rpc({
////                 route: "/shop/resolvepay/get_sale_order",
////             })
////             .then((orderInfo) => {
////                 if (!orderInfo) {
////                     alert('You do not have enough credit')
////                     return
////                 }
////                 resolve.checkout({
////                     sandbox: true, // INCLUDE ONLY IF USING SANDBOX ENVIRONMENT (default is production)
////                     merchant: {
////                       id:          'linusbike',
////                       success_url: window.location.origin + '/resolvepay/confirm',
////                       cancel_url:  window.location.origin + '/resolvepay/cancel'
////                     },
////                     customer: {
////                       ...orderInfo.customer
////                     },
////                     shipping: {
////                       ...orderInfo.shipping
////                     },
////                     billing: {
////                       ...orderInfo.billing
////                     },
////                     items: orderInfo.items,
//
////                     order_number: orderInfo.order_number, // (optional) merchant order number
////                     po_number:    '', // (optional) buyer purchase order number if required
//
////                     shipping_amount:  0.00,
////                     tax_amount:       orderInfo.tax_amount,
////                     total_amount:     orderInfo.total_amount,
////                 });
////             });
////         }
////     });
//// });
//
//// odoo.define('syncoria_resolvepay.payment_checkout', function (require) {
////     "use strict";
//
////     var rpc = require('web.rpc');
////     console.log('test')
////     $(document).on('click', '#resolvepay_direct_checkout', function () {
////         console.log("test")
////         return rpc.query({
////             model: 'resolvepay.instance',
////             method: 'get_sale_order',
////             args: [],
////             kwargs: {},
////         })
////         .then(function (test) {
////             console.log(test)
////         })
////     })
//// });