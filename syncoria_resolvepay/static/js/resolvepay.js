odoo.define('syncoria_resolvepay.payment_checkout', require => {
    'use strict';

    var publicWidget = require('web.public.widget');

    const core = require("web.core");
    const ajax = require("web.ajax");

    const checkoutForm = require("payment.checkout_form");
    const manageForm = require("payment.manage_form");
    const Dialog = require("web.Dialog");

    const resolvePayCheckoutMixin = {
        _onClickPay: async function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            // Check that the user has selected a payment option
            const $checkedRadios = this.$('input[name="o_payment_radio"]:checked');
            if (!this._ensureRadioIsChecked($checkedRadios)) {
                return;
            }
            const checkedRadio = $checkedRadios[0];

            // Extract contextual values from the radio button
            const provider = this._getProviderFromRadio(checkedRadio);
            const paymentOptionId = this._getPaymentOptionIdFromRadio(checkedRadio);
            const flow = this._getPaymentFlowFromRadio(checkedRadio);

            // Update the tx context with the value of the "Save my payment details" checkbox
            if (flow !== 'token') {
                const $tokenizeCheckbox = this.$(
                    `#o_payment_acquirer_inline_form_${paymentOptionId}` // Only match acq. radios
                ).find('input[name="o_payment_save_as_token"]');
                this.txContext.tokenizationRequested = $tokenizeCheckbox.length === 1
                    && $tokenizeCheckbox[0].checked;
            } else {
                this.txContext.tokenizationRequested = false;
            }

            // Make the payment
            this._hideError(); // Don't keep the error displayed if the user is going through 3DS2
            this._disableButton(true); // Disable until it is needed again
            $('body').block({
                message: false,
                overlayCSS: { backgroundColor: "#000", opacity: 0, zIndex: 1050 },
            });
            const $poNumber = this.$('input[name="po_number"]');
            const po_number = await this._rpc({route: "/shop/add_po_number",  params: {po: $poNumber[0].value}})
            if (paymentOptionId == 18) {
                const validate_credit = await this._rpc({route: "/shop/validate_credit",  params: {partner: this.txContext.partnerId, amount: this.txContext.amount}})
                if (!validate_credit) {
                    window.location.replace('/resolvepay/pre_confirmation');
                }
            }

            this._processPayment(provider, paymentOptionId, flow);
        },

        /**
           *
           * @override method from payment.payment_form_mixin
           * @private
           * @param {string} provider - The provider of the payment option's acquirer
           * @param {number} paymentOptionId - The id of the payment option handling the transaction
           * @param {string} flow - The online payment flow of the transaction
           * @return {Promise}
           */
        //      _processPayment: function(provider, paymentOptionId, flow) {
        //        console.log("--------------------------------------");
        //        console.log("Resolve Pay ==>>>_processPayment ===>>>>");
        //        console.log("provider ===>>>>", provider);
        //        console.log("paymentOptionId ===>>>>", paymentOptionId);
        //        console.log("flow ===>>>>", flow);
        //        console.log("--------------------------------------");
        //        const po = document.querySelector('#customer_reference')
        //        const order_type = document.querySelector('#order_type')
        //        if (po && order_type) {
        //          let result = this._rpc({route: "/shop/add_po_ordertype",  params: {po: po.value, order_type: order_type.value}})
        //        }
        //        if (paymentOptionId != 18) {
        //          return this._super(...arguments);
        //        }
        //
        //        if (paymentOptionId == 18) {
        //          return this._rpc({
        //                route: "/shop/resolvepay/get_sale_order",
        //            })
        //            .then((orderInfo) => {
        //                if (!orderInfo) {
        //                    window.location.replace('/resolvepay/pre_confirmation');
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
    }
    checkoutForm.include(resolvePayCheckoutMixin);
    manageForm.include(resolvePayCheckoutMixin);
});




















//     publicWidget.registry.ResolvePayButton = publicWidget.Widget.extend({
//         selector: '#resolvepay_direct_checkout',
//         events: {
//             'click': '_onClick',
//         },

//         _onClick: function () {
//             return this._rpc({
//                 route: "/shop/resolvepay/get_sale_order",
//             })
//             .then((orderInfo) => {
//                 if (!orderInfo) {
//                     alert('You do not have enough credit')
//                     return
//                 }
//                 resolve.checkout({
//                     sandbox: true, // INCLUDE ONLY IF USING SANDBOX ENVIRONMENT (default is production)
//                     merchant: {
//                       id:          'linusbike',
//                       success_url: window.location.origin + '/resolvepay/confirm',
//                       cancel_url:  window.location.origin + '/resolvepay/cancel'
//                     },
//                     customer: {
//                       ...orderInfo.customer
//                     },
//                     shipping: {
//                       ...orderInfo.shipping
//                     },
//                     billing: {
//                       ...orderInfo.billing
//                     },
//                     items: orderInfo.items,

//                     order_number: orderInfo.order_number, // (optional) merchant order number
//                     po_number:    '', // (optional) buyer purchase order number if required

//                     shipping_amount:  0.00,
//                     tax_amount:       orderInfo.tax_amount,
//                     total_amount:     orderInfo.total_amount,
//                 });
//             });
//         }
//     });
// });

// odoo.define('syncoria_resolvepay.payment_checkout', function (require) {
//     "use strict";

//     var rpc = require('web.rpc');
//     console.log('test')
//     $(document).on('click', '#resolvepay_direct_checkout', function () {
//         console.log("test")
//         return rpc.query({
//             model: 'resolvepay.instance',
//             method: 'get_sale_order',
//             args: [],
//             kwargs: {},
//         })
//         .then(function (test) {
//             console.log(test)
//         })
//     })
// });