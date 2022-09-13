from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.controllers.main import Website


class WebsiteSaleInherit(WebsiteSale):

    @http.route(['/shop/confirmation'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            tag_id = request.env['crm.tag'].sudo().search([('name', '=', 'B2B')])
            if tag_id:
                order.tag_ids = [(4, tag_id.id)]
            return request.render("website_sale.confirmation", {
                'order': order,
                'order_tracking_info': self.order_2_return_dict(order),
            })
        else:
            return request.redirect('/shop')

    def sitemap_shop(env, rule, qs):
        if not qs or qs.lower() in '/shop':
            yield {'loc': '/shop'}

        Category = env['product.public.category']
        dom = sitemap_qs2dom(qs, '/shop/category', Category._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for cat in Category.search(dom):
            loc = '/shop/category/%s' % slug(cat)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    @http.route([
        '''/shop''',
        '''/shop/page/<int:page>''',
        '''/shop/category/<model("product.public.category"):category>''',
        '''/shop/category/<model("product.public.category"):category>/page/<int:page>'''
    ], type='http', auth="user", website=True, sitemap=sitemap_shop)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        res = super(WebsiteSaleInherit, self).shop(page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post)
        return res


class WebsiteInherit(Website):

    @http.route('/', type='http', auth="user", website=True, sitemap=True)
    def index(self, **kw):
        res = super(WebsiteInherit, self).index(**kw)
        return res
