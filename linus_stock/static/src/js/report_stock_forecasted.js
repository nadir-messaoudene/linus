odoo.define('linus_stock.stock_forecast', require => {
    'use strict';
    const { loadLegacyViews } = require("@web/legacy/legacy_views");

    const StockReplenishReport = require('stock.ReplenishReport');

    const ReplenishReportInherit = {
        /**
         * @override
         */
        init: function (parent, action, options) {
            console.log("init inherit")
            this._super.apply(this, arguments);
            this.context = action.context;
            console.log(this.context)
            this.productId = this.context.active_id;
            this.resModel = this.context.active_model || this.context.params.active_model || 'product.template';
            const isTemplate = this.resModel === 'product.template';
            this.actionMethod = `action_product_${isTemplate ? 'tmpl_' : ''}forecast_report`;
            const reportName = `report_product_${isTemplate ? 'template' : 'product'}_replenishment`;
            this.report_url = `/report/html/stock.${reportName}/${this.productId}`;
            this._title = action.name;

            var loadWarehouses = this._rpc({
                model: 'report.stock.report_product_product_replenishment',
                method: 'get_warehouses',
                context: this.context,
            }).then((res) => {
                console.log(res)
                const active_warehouse = res.find(w => w.id == action.context.warehouse);
                if (!active_warehouse){
                    console.log('if (!this.active_warehouse){ INIT')
                    action.context.warehouse = res[0].id;
                }
            });
            this.context = action.context;
        },
    }
    StockReplenishReport.include(ReplenishReportInherit)
})