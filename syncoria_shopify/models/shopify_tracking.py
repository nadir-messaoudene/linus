# import logging
# from odoo import models, fields, exceptions,api, _

# logger = logging.getLogger(__name__)
# try:
#     import requests
# except ImportError:
#     logger.info("Unable to import requests, please install it with pip install requests")

# class SaleOrderInherit(models.Model):
#     _inherit = 'sale.order'

#     def shopify_update_track(self, track_data):
#         # Get Entity_id from shopify
#         order_URL = '/rest/V1/orders/?searchCriteria[filter_groups][0][filters][0][field]=increment_id'
#         order_URL = order_URL + '&searchCriteria[filter_groups][0][filters][0][value]='+ str(self.shopify_id)
#         order_URL = order_URL + '&searchCriteria[filter_groups][0][filters][0][condition_type]=eq'
#         order = self.env['shopify.connector'].shopify_api_call(headers={}, url=order_URL, type='GET', data={})    
#         if len(order['items'])> 0:
#             order_id = order['items'][0]['entity_id']
#             url = '/rest/V1/order/' + str(order_id) + '/ship'
#             # carrier_tracking_ref
#             data = {   
#                         "notify": False,
#                         "appendComment": True,
#                         "comment": {
#                         "extension_attributes": {},
#                         "comment": "Shipment created on Odoo",
#                         "is_visible_on_front": 1
#                         },
#                         "tracks": [
#                                 track_data
#                             ]
#                     }
#             track = self.env['shopify.connector'].shopify_api_call(headers={'Content-Type':'application/json'}, url=url, type='POST', data=data)
#             logger.info("--------------")
#             logger.info(order)  
#             logger.info(track)
#             logger.info("--------------")
#             return track
#             # {'message': "Shipment Document Validation Error(s):\nThe order does not allow a shipment to be created.\nYou can't create a shipment without products.", 'trace': "#0 [internal function]: shopify\\Sales\\Model\\ShipOrder->execute(7917, Array, false, true, Object(shopify\\Sales\\Model\\Order\\Shipment\\CommentCreation), Array, Array, NULL)\n#1 /srv/public_html/vendor/shopify/module-webapi/Controller/Rest/SynchronousRequestProcessor.php(95): call_user_func_array(Array, Array)\n#2 /srv/public_html/vendor/shopify/module-webapi/Controller/Rest.php(188): shopify\\Webapi\\Controller\\Rest\\SynchronousRequestProcessor->process(Object(shopify\\Framework\\Webapi\\Rest\\Request\\Proxy))\n#3 /srv/public_html/vendor/shopify/framework/Interception/Interceptor.php(58): shopify\\Webapi\\Controller\\Rest->dispatch(Object(shopify\\Framework\\App\\Request\\Http))\n#4 /srv/public_html/vendor/shopify/framework/Interception/Interceptor.php(138): shopify\\Webapi\\Controller\\Rest\\Interceptor->___callParent('dispatch', Array)\n#5 /srv/public_html/vendor/shopify/framework/Interception/Interceptor.php(153): shopify\\Webapi\\Controller\\Rest\\Interceptor->shopify\\Framework\\Interception\\{closure}(Object(shopify\\Framework\\App\\Request\\Http))\n#6 /srv/public_html/generated/code/shopify/Webapi/Controller/Rest/Interceptor.php(26): shopify\\Webapi\\Controller\\Rest\\Interceptor->___callPlugins('dispatch', Array, Array)\n#7 /srv/public_html/vendor/shopify/framework/App/Http.php(137): shopify\\Webapi\\Controller\\Rest\\Interceptor->dispatch(Object(shopify\\Framework\\App\\Request\\Http))\n#8 /srv/public_html/generated/code/shopify/Framework/App/Http/Interceptor.php(24): shopify\\Framework\\App\\Http->launch()\n#9 /srv/public_html/vendor/shopify/framework/App/Bootstrap.php(261): shopify\\Framework\\App\\Http\\Interceptor->launch()\n#10 /srv/public_html/pub/index.php(251): shopify\\Framework\\App\\Bootstrap->run(Object(shopify\\Framework\\App\\Http\\Interceptor))\n#11 {main}"} 

#         else:
#             return{'error':True,'message':'No Orders found on shopify'}

