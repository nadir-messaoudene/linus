odoo.define('linus_website.VariantMixin', function (require) {
'use strict';
const {Markup} = require('web.utils');
var VariantMixin = require('website_sale_stock.VariantMixin');
var publicWidget = require('web.public.widget');
var ajax = require('web.ajax');
var core = require('web.core');
var QWeb = core.qweb;

const loadXml = async () => {
    return ajax.loadXML('/linus_website/static/src/xml/product_availability.xml', QWeb);
};

require('website_sale.website_sale');

VariantMixin._onChangeCombinationStock = function (ev, $parent, combination) {
    let product_id = 0;
    // needed for list view of variants
    if ($parent.find('input.product_id:checked').length) {
        product_id = $parent.find('input.product_id:checked').val();
    } else {
        product_id = $parent.find('.product_id').val();
    }
    const isMainProduct = combination.product_id &&
        ($parent.is('.js_main_product') || $parent.is('.main_product')) &&
        combination.product_id === parseInt(product_id);

    if (!this.isWebsite || !isMainProduct) {
        return;
    }

    const $addQtyInput = $parent.find('input[name="add_qty"]');
    let qty = $addQtyInput.val();

    $parent.find('#add_to_cart').removeClass('out_of_stock');
    $parent.find('.o_we_buy_now').removeClass('out_of_stock');
    if (combination.product_type === 'product' && !combination.allow_out_of_stock_order) {
        combination.free_qty -= parseInt(combination.cart_qty);
        $addQtyInput.data('max', combination.free_qty || 1);
        if (combination.free_qty < 0) {
            combination.free_qty = 0;
        }
        if (qty > combination.free_qty) {
            qty = combination.free_qty || 1;
            $addQtyInput.val(qty);
        }
        if (combination.free_qty < 1) {
            $parent.find('#add_to_cart').addClass('disabled out_of_stock');
            $parent.find('.o_we_buy_now').addClass('disabled out_of_stock');
        }
    }

    loadXml().then(function (result) {
        $('.oe_website_sale')
            .find('.availability_message_' + combination.product_template)
            .remove();
        combination.has_out_of_stock_message = $(combination.out_of_stock_message).text() !== '';
        combination.out_of_stock_message = Markup(combination.out_of_stock_message);
        const $message = $(QWeb.render(
            'linus_website.product_availability',
            combination
        ));
        console.log($message)
        $('div.custom_availability_messages').html($message);
    });
};
return VariantMixin;

});