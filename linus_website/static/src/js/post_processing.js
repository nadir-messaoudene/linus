odoo.define('linus_website.post_processing', function (require) {
    'use strict';
    var publicWidget = require('web.public.widget');
//    var PaymentPostProcessing = require('@payment/js/post_processing')[Symbol.for("default")].paymentPostProcessing;
//    console.log('loaded')
    publicWidget.registry.PaymentPostProcessing.include({
        xmlDependencies: (publicWidget.registry.PaymentPostProcessing.prototype.xmlDependencies || []).concat(
        ['/linus_website/static/src/xml/payment.xml']
        ),
    });
//    console.log(publicWidget.registry.PaymentPostProcessing.prototype.xmlDependencies);
});