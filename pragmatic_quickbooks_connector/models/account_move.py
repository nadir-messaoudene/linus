# -*- coding: utf-8 -*-
import json
import logging
import re
from lxml import etree
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.fields import Command
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.move"


    qbo_invoice_id = fields.Char("QBO Invoice Id", copy=False, help="QBO Invoice Id")
    qbo_invoice_name = fields.Char("QBO Invoice Name", copy=False, help="QBO Invoice Name")
    tax_state = fields.Selection(
        [('inclusive', 'Tax Inclusive'), ('exclusive', 'Tax Exclusive'), ('notapplicable', 'Not Applicable')],
        string='Tax Status', default="exclusive")

    # @api.model
    # def create(self, vals):
    #     _logger.info('Invoice Create Vals Before: {}'.format(vals))
    #     res = super(AccountInvoice, self).create(vals)
    #     return res

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ Set the correct domain for `partner_id`, depending on invoice type """
        result = super(AccountInvoice, self)._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        _logger.info("CONTEXT IS ---------------> {}".format(self._context))
        document_type = self._context.get('default_move_type')
        _logger.info("DOCUMENT TYPE IS --> {}".format(document_type))
        if view_type == 'form':
            doc = etree.XML(result['arch'])
            node = doc.xpath("//field[@name='partner_id']")[0]
            if document_type == 'in_invoice':
                _logger.info("DOCUMENT IS OF TYPE VENDOR BILL")
                node.set('domain', "[('supplier_rank', '>=', 1)]")
            if document_type == 'out_invoice':
                _logger.info("DOCUMENT IS OF TYPE CUSTOMER INVOICE")
                node.set('domain', "[('customer_rank', '>=', 1)]")
            if document_type == 'out_refund':
                _logger.info("DOCUMENT IS OF TYPE CUSTOMER CREDIT NOTE")
                node.set('domain', "[('customer_rank', '>=', 1)]")
            if document_type == 'in_refund':
                _logger.info("DOCUMENT IS OF TYPE  VENDOR CREDIT NOTE")
                node.set('domain', "[('supplier_rank', '>=', 1)]")
            result['arch'] = etree.tostring(doc)
        return result



    def check_account_id(self, cust):
        '''
        This function will check if for a particular product account exists or not
        '''

        if cust.get('Line'):
            for lines in cust.get('Line'):
                if 'SalesItemLineDetail' in lines and lines.get('SalesItemLineDetail').get('ItemRef').get('value'):
                    _logger.info("Checking for acc id ......")
                    res_product = self.env['product.product'].search(
                        [('qbo_product_id', '=', lines.get('SalesItemLineDetail').get('ItemRef').get('value'))])
                    if res_product:
                        if res_product.property_account_income_id or res_product.categ_id.property_account_income_categ_id:
                            _logger.info("Product/Category has income and expense account set ")
                            return True
                        else:
                            return False

    @api.model
    def check_if_lines_present(self, cust):
        if cust.get('Line'):
            for i in cust.get('Line'):
                if i.get('SalesItemLineDetail'):
                    return True
                else:
                    return False
        else:
            return False

    @api.model
    def check_if_lines_present_vendor_bill(self, cust):
        if 'Line' in cust and cust.get('Line'):
            for i in cust.get('Line'):
                if i.get('ItemBasedExpenseLineDetail') or i.get('AccountBasedExpenseLineDetail'):
                    if i.get('ItemBasedExpenseLineDetail'):
                        _logger.info("ItemBasedExpenseLineDetail-----------------> {}".format(i.get('ItemBasedExpenseLineDetail')))
                    elif i.get('AccountBasedExpenseLineDetail'):
                        _logger.info("AccountBasedExpenseLineDetail-----------------> {}".format(i.get('AccountBasedExpenseLineDetail')))
                    return True
                else:
                    _logger.info("NO ItemBasedExpenseLineDetail or NO AccountBasedExpenseLineDetail ")
                    return False
        else:
            return False

    def single_import_partner(self, qbo_id):
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        company = self.env['res.company'].browse(1)
        _logger.info("Company is   :-> {} ".format(company))
        query = "select * from Customer WHERE Id = '%s'" % (qbo_id)
        url_str = company.get_import_query_url()
        # url = url_str.get('url') + '/query?%squery=%s' % (
        #     'minorversion=' + url_str.get('minorversion') + '&' if url_str.get('minorversion') else '', query)
        url = url_str.get('url') + '/customer/%s' % (qbo_id)
        data = requests.request('GET', url, headers=url_str.get('headers'), verify=False)
        _logger.info(url)
        _logger.info("Customer data is *************** {}".format(data.text))
        if data.status_code == 200:
            partner = self.env['res.partner'].create_partner(data, is_customer=True)
            return partner
        else:
            raise UserError("Empty Data")
            _logger.warning(_('Empty data'))

    def single_import_vendor(self, qbo_id):
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        company = self.env['res.company'].browse(1)
        _logger.info("Company is   :-> {} ".format(company))
        query = "select * from Vendor WHERE Id = '%s'" % (qbo_id)
        url_str = company.get_import_query_url()
        url = url_str.get('url') + '/query?%squery=%s' % (
            'minorversion=' + url_str.get('minorversion') + '&' if url_str.get('minorversion') else '', query)
        data = requests.request('GET', url, headers=url_str.get('headers'), verify=False)
        _logger.info(url)
        _logger.info("Vendor data is *************** {}".format(data.text))
        if data.status_code == 200:
            partner = self.env['res.partner'].create_partner(data, is_vendor=True)
            return partner
        else:
            raise UserError("Empty Data")
            _logger.warning(_('Empty data'))

    # def single_import_chart_of_account(self, qbo_id):
    #     company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
    #     _logger.info("Company is   :-> {} ".format(company))
    #     query = "select * from Account WHERE Id = '%s'" % (qbo_id)
    #     url_str = company.get_import_query_url()
    #     url = url_str.get('url') + '/query?%squery=%s' % (
    #         'minorversion=' + url_str.get('minorversion') + '&' if url_str.get('minorversion') else '', query)
    #     data = requests.request('GET', url, headers=url_str.get('headers'), verify=False)
    #     _logger.info(url)
    #     _logger.info("Account data is *************** {}".format(data.text))
    #     if data.status_code == 200:
    #         acc = self.env['account.account'].create_account_account(data)
    #         return acc
    #     else:
    #         raise UserError("Empty Data")
    #         _logger.warning(_('Empty data'))

    def create_invoice_dict(self, cust, type):
        dict_i = {}
        if type == 'out_invoice' or type == 'out_refund':
            partner_type = 'CustomerRef'
        if type == 'in_invoice':
            partner_type = 'VendorRef'
        # print ("assssssssssssssssssssssssssssssssssssss", cust.get(partner_type).get('value'))
        if type == 'in_invoice':
            res_partner = self.env['res.partner'].search([('qbo_vendor_id', '=', cust.get(partner_type).get('value'))], limit=1)
            if not res_partner:
                res_partner = self.single_import_vendor(cust.get(partner_type).get('value'))
        else:
            res_partner = self.env['res.partner'].search([('qbo_customer_id', '=', cust.get(partner_type).get('value'))], limit=1)
            if not res_partner:
                # if '(deleted)' in cust.get(partner_type).get('name'):
                #     _logger.info("Partner is deleted ---> Id:{} Name: {}".format(cust.get(partner_type).get('value'), cust.get(partner_type).get('name')))
                #     return False
                # else:
                res_partner = self.single_import_partner(cust.get(partner_type).get('value'))

        _logger.info("Partner is ---> {}".format(res_partner))

        if res_partner:
            if cust.get('Id'):
                dict_i['partner_id'] = res_partner.id
                dict_i['qbo_invoice_id'] = cust.get('Id')
                dict_i['company_id'] = self.env.user.company_id.id
                dict_i['move_type'] = type

            if cust.get('CurrencyRef'):
                if cust.get('CurrencyRef').get('value'):
                    curr = cust.get('CurrencyRef').get('value')
                    _logger.info("Currency Value for invoice import ------> %s"%(curr))
                    currency = self.env['res.currency'].search([('name', '=', curr)],
                                                               limit=1)
                    if not currency:
                        raise UserError(_("Please activate the currency %s") % (cust.get('CurrencyRef').get('value')))

                    dict_i['currency_id'] = currency.id

            if res_partner.customer_rank:
                sale = self.env['account.journal'].sudo().search([('type', '=', 'sale'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                if sale:
                    dict_i['journal_id'] = sale.id
                else:
                    raise UserError("Please Define Sale Journal")
#                     sale = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
#                     if sale:
#                         dict_i['journal_id'] = sale.id

            if res_partner.supplier_rank:
                purchase = self.env['account.journal'].sudo().search([('type', '=', 'purchase'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                if purchase:
                    dict_i['journal_id'] = purchase.id
                else:
                    raise UserError("Please Define Purchase Journal")
#                     purchase = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
#                     if purchase:
#                         dict_i['journal_id'] = purchase.id

            if cust.get('DocNumber'):
                dict_i['qbo_invoice_name'] = cust.get('DocNumber')
                # dict_i['number'] = cust.get('DocNumber')

            # to set tax state from qbo
            if cust.get('GlobalTaxCalculation'):
                if cust.get('GlobalTaxCalculation') == 'TaxExcluded':
                    dict_i['tax_state'] = 'exclusive'
                elif cust.get('GlobalTaxCalculation') == 'TaxInclusive':
                    dict_i['tax_state'] = 'inclusive'
                elif cust.get('GlobalTaxCalculation') == 'NotApplicable':
                    dict_i['tax_state'] = 'notapplicable'

            if cust.get('DueDate'):
                dict_i['invoice_date_due'] = cust.get('DueDate')

            if cust.get('TxnDate'):
                dict_i['invoice_date'] = cust.get('TxnDate')
        if not dict_i.get('partner_id'):
            raise UserError("Please Import "+partner_type+" for QBO Id "+str(cust.get(partner_type).get('value')))
        return dict_i

    def import_invoice(self):
        company = self.env['res.users'].search([('id', '=', 2)]).company_id
        company = self.env['res.company'].browse(1)
        # company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        if company.access_token:
            headers = {}
            headers['Authorization'] = 'Bearer ' + company.access_token
            headers['accept'] = 'application/json'
            headers['Content-Type'] = 'text/plain'
            # query = "select * from invoice WHERE Id = '186075'"
            query = "select * from invoice WHERE Id > '%s' AND TxnDate >= '%s' AND TxnDate <= '%s' order by Id STARTPOSITION %s MAXRESULTS %s " % (
                company.quickbooks_last_invoice_imported_id, company.date_from, company.date_to, company.start, company.limit)
            # query = "select * from invoice WHERE Id = '%s' order by Id STARTPOSITION %s MAXRESULTS %s " % (119, company.start, company.limit)
            data = requests.request('GET', company.url + str(company.realm_id) + "/query?query=" + query,headers=headers)
            if data.status_code == 200:
                self.create_invoice(data, 'out_invoice')
            else:
                _logger.error(data)
                raise UserError(data)


    def import_credit_memo(self):
        # company = self.env['res.users'].search([('id', '=', 2)]).company_id
        company = self.env['res.company'].browse(1)
        if company.access_token:
            headers = {}
            headers['Authorization'] = 'Bearer ' + company.access_token
            headers['accept'] = 'application/json'
            headers['Content-Type'] = 'text/plain'

            # query = "select * from CreditMemo WHERE Id > '%s' order by Id" % (company.quickbooks_last_credit_note_imported_id)
            query = "select * from CreditMemo WHERE Id > '%s' AND TxnDate >= '%s' AND TxnDate <= '%s' order by Id STARTPOSITION %s MAXRESULTS %s " % (
                company.quickbooks_last_credit_note_imported_id, company.date_from, company.date_to, company.start,
                company.limit)
            data = requests.request('GET', company.url + str(company.realm_id) + "/query?query=" + query,
                                    headers=headers)
            if data.status_code == 200:
                self.create_invoice(data, 'out_refund')
            else:
                _logger.error(data)
                raise UserError('Connection Error...!')

    def import_refund(self):
        company = self.env['res.company'].browse(1)
        if company.access_token:
            headers = {}
            headers['Authorization'] = 'Bearer ' + company.access_token
            headers['accept'] = 'application/json'
            headers['Content-Type'] = 'text/plain'

            # query = "select * from CreditMemo WHERE Id > '%s' order by Id" % (company.quickbooks_last_credit_note_imported_id)
            query = "select * from refundreceipt WHERE Id > '%s' AND TxnDate >= '%s' AND TxnDate <= '%s' order by Id STARTPOSITION %s MAXRESULTS %s " % (
                company.quickbooks_last_refund_imported_id, company.date_from, company.date_to, company.start,
                company.limit)
            data = requests.request('GET', company.url + str(company.realm_id) + "/query?query=" + query,
                                    headers=headers)
            if data.status_code == 200:
                self.create_refund(data, 'out_refund')
            else:
                _logger.error(data)
                raise UserError('Connection Error...!')

    def import_vendor_bill(self):
        # print ("------------------------------------------------------------------------000000000000000000000000")
        company = self.env['res.users'].search([('id', '=', 2)]).company_id

        _logger.info("inside vendor bill ****************************")
        company = self.env['res.company'].browse(1)
        if company.access_token:
            headers = {}
            headers['Authorization'] = 'Bearer ' + company.access_token
            headers['accept'] = 'application/json'
            headers['Content-Type'] = 'text/plain'
            # query = "select * from Bill WHERE Id > '%s' order by Id" % (
            #     company.quickbooks_last_vendor_bill_imported_id)
            query = "select * from bill WHERE Id > '%s' AND MetaData.CreateTime >= '%s' AND MetaData.CreateTime <= '%s' order by Id STARTPOSITION %s MAXRESULTS %s " % (
                company.quickbooks_last_vendor_bill_imported_id, company.date_from, company.date_to, company.start,
                company.limit)
            data = requests.request('GET', company.url + str(company.realm_id) + "/query?query=" + query, headers=headers)
            if data.status_code == 200:
                self.create_invoice(data, 'in_invoice')
            else:
                _logger.info(data)
                raise UserError("Connection Error !!!")


    def create_invoice(self, data, type='out_invoice'):

        # print ("\n\n------------------------------------------------------------------------1111111111111111111",data,data.text,type)
        company = self.env['res.users'].search([('id', '=', self._uid)]).company_id
        company = self.env['res.company'].browse(1)
        if data:
            recs = []
            parsed_data = json.loads(str(data.text))
            count = 0
            if parsed_data:
                if type == 'out_invoice':
                    get_data_for = 'Invoice'
                elif type == 'out_refund':
                    get_data_for = 'CreditMemo'
                if type == 'in_invoice':
                    get_data_for = 'Bill'

                if parsed_data.get('QueryResponse') and parsed_data.get('QueryResponse').get(get_data_for):
                    for cust in parsed_data.get('QueryResponse').get(get_data_for):
                        return_val = self.check_account_id(cust)
                        _logger.info("QB Invoice Data -----> {}".format(cust))
                        # print("----- in vendor bill--",)
                        # if return_val and type != 'in_invoice':
                        #     if type == 'out_invoice' or type == 'out_refund':
                        #         line_present = self.check_if_lines_present(cust)
                        #         _logger.info('ORDER LINES PRESENT IN INVOICE :: %s', line_present)
                        #     if not line_present:
                        #         continue
                        # elif not return_val and type == 'in_invoice':
                        #     if type == 'in_invoice':
                        #         line_present = self.check_if_lines_present_vendor_bill(cust)
                        #         _logger.info('ORDER LINES PRESENT IN BILL :: %s', line_present)
                        #     if not line_present:
                        #         continue

                        # print (cust, " ------------------------------------------------------------------ 111")
                        count = count + 1
                        account_invoice = self.env['account.move'].search([('qbo_invoice_id', '=', cust.get('Id'))])
                        _logger.info("ACC invoice is -----> {}".format(account_invoice))
                        # try:
                        if not account_invoice:
                            _logger.info("Attempting for Invoice Creation")
                            _logger.info("QBO obj is -----> {}".format(cust))
                            dict_i = self.create_invoice_dict(cust, type)
                            # if not dict_i:
                            #     continue
                            dict_i['invoice_line_ids'] = []
                            invoice_obj = self.env['res.partner'].search([('id', '=', dict_i.get('partner_id'))],
                                                                         limit=1)
                            invoice_line = self.odoo_create_invoice_line_dict(cust, invoice_obj, type,dict_i.get('qbo_invoice_id'))
                            # if not invoice_line:
                            #     continue
                            if invoice_line:
                                for k in invoice_line:
                                    if 'exclude_from_invoice_tab' in k and not k['exclude_from_invoice_tab']:
                                        dict_i['invoice_line_ids'].append((0, 0, k))
                                    elif 'exclude_from_invoice_tab' not in k:
                                        dict_i['invoice_line_ids'].append((0, 0, k))
                                # return True
                                _logger.info("Dictionary for f is ---> {}".format(dict_i))
                                invoice_obj = self.env['account.move'].create(dict_i)
                                # _logger.info("Invoice obj is -----> {}".format(invoice_obj))

                                if not invoice_obj.posted_before:

                                    invoice_obj.action_post()
                                    # invoice_line = self.create_invoice_line_dict(cust, invoice_obj, type)
                                    # _logger.info("Attempting for Invoice Line Creation!")
                                    # create_p = self.env['account.move.line'].create(invoice_line)
                                    # if create_p:
                                    # self._cr.commit()
                                    _logger.info("Invoice Line Committed!!!")

                                    if type == 'out_invoice':
                                        company.quickbooks_last_invoice_imported_id = cust.get('Id')
                                    elif type == 'out_refund':
                                        company.quickbooks_last_credit_note_imported_id = cust.get('Id')
                                    elif type == 'in_invoice':
                                        company.quickbooks_last_vendor_bill_imported_id = cust.get('Id')
                                    else:

                                        _logger.error("Invoice line was not created.")
                                    print(cust)
                                    linked_document = cust.get('LinkedTxn', {})
                                    for document in linked_document:
                                        if document.get('TxnType') == 'Payment':
                                            payment_id = document.get('TxnId')
                                            company.import_payment(payment_id)
                                else:
                                    _logger.error("NO ACCOUNT ID WAS ATTACHED !")
                            else:
                                _logger.error("NO Line Found for Invoice!")


                        else:
                            _logger.info("Begin updating taxes!")
                            account_invoice.button_draft()
                            for invoice_line in account_invoice.invoice_line_ids:
                                account_invoice.write({'invoice_line_ids': [Command.delete(invoice_line.id)]})
                            dict_i = {'invoice_line_ids': []}
                            invoice_obj = account_invoice.partner_id
                            invoice_line = self.odoo_create_invoice_line_dict(cust, invoice_obj, type, dict_i.get('qbo_invoice_id'))
                            if invoice_line:
                                for k in invoice_line:
                                    if not k['exclude_from_invoice_tab']:
                                        if cust.get('TxnTaxDetail') and cust.get('TxnTaxDetail').get('TotalTax') == 0:
                                            k['tax_ids'] = False
                                        dict_i['invoice_line_ids'].append((0, 0, k))
                                _logger.info("Dictionary for invoice line is ---> {}".format(dict_i))
                                account_invoice.write(dict_i)
                            account_invoice.action_post()
                            # else:
                            #     _logger.error("NO Line Found for Invoice!")
                            #     f = open(r"C:\pyproj\Odoo 15\Syncoria\linus\msg.txt", "a")
                            #     f.write(account_invoice.name + '\n')
                            #     f.close()
                            #     continue





                            # account_invoice.button_draft()
                            # discount_line = account_invoice.invoice_line_ids.filtered(lambda l: l.name == 'Discount')
                            # tax_ids = self.odoo_create_invoice_line_dict_discount_tax(cust, type)
                            # for discount_l in discount_line:
                            #     discount_l.write({'tax_ids': tax_ids})
                            #     account_invoice.write(
                            #         {'invoice_line_ids': [Command.update(discount_l.id, {'tax_ids': tax_ids})]})




                            # account_invoice.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True)
                            # account_invoice.action_post()
                            # _logger.info("Starting mapping payment ---> {}".format(account_invoice.name))
                            # pay_term_lines = account_invoice.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                            # domain = [
                            #     ('account_id', 'in', pay_term_lines.account_id.ids),
                            #     ('parent_state', '=', 'posted'),
                            #     ('partner_id', '=', account_invoice.commercial_partner_id.id),
                            #     ('reconciled', '=', False),
                            #     '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
                            # ]
                            # if account_invoice.is_inbound():
                            #     domain.append(('balance', '<', 0.0))
                            #     domain.append(('ref', '=', account_invoice.name))
                            # move_payment_lines = self.env['account.move.line'].search(domain)
                            # for line in move_payment_lines:
                            #     account_invoice.js_assign_outstanding_line(line.id)
                            _logger.info("End updating taxes!")
                            if type == 'out_invoice':
                                company.quickbooks_last_invoice_imported_id = cust.get('Id')
                            elif type == 'out_refund':
                                company.quickbooks_last_credit_note_imported_id = cust.get('Id')
                            elif type == 'in_invoice':
                                company.quickbooks_last_vendor_bill_imported_id = cust.get('Id')
                            _logger.info("All data seems to be imported successfully!")
                            # raise UserError("All data seems to be imported!")
#                                 _logger.info("Attempting to update the invoice!")
#                                 print("contes1!!!!!!!!!!!!!!!!!!!!!!!!11",self._context)
#
#                                 dict_i = self.create_invoice_dict(cust, type)
#                                 _logger.info("Dictionary for updation is ---> {}".format(dict_i))
#                                 write_inv = account_invoice.write(dict_i)
#                                 if write_inv:
#                                     _logger.info('Invoice Updated Successfully..!! :: %s', cust.get('Id'))
# #                                     invoice_line = self.create_invoice_line_dict(cust, account_invoice, type)
#                                     invoice_line = self.update_invoice_line_dict(cust,account_invoice,type)
#                                     _logger.info("Dictionary for updating move line is ---> {}".format(invoice_line))
#                                     for line in invoice_line:
#                                         print("line us 1!!!!!!!!!!",line)
#                                         write_p = self.env['account.move.line'].write(invoice_line)
#                                         if write_p:
#                                             self._cr.commit()
#                                             _logger.info("Invoice Line Updated!!!")
#                                             if type == 'out_invoice':
#                                                 company.quickbooks_last_invoice_imported_id = cust.get('Id')
#                                             elif type == 'out_refund':
#                                                 company.quickbooks_last_credit_note_imported_id = cust.get('Id')
#                                             elif type == 'in_invoice':
#                                                 company.quickbooks_last_vendor_bill_imported_id = cust.get('Id')
#                                         else:
#
#                                             _logger.error("Invoice line was not updated.")
#                                 else:
#                                     _logger.error("NO ACCOUNT ID WAS ATTACHED !")
    #                     except Exception as e:
    #                         _logger.error(_('Error : %s' % e))
    #                         raise ValidationError(_('Error : %s' % e))
                            # pass
                else:
                    raise UserError("It seems that all of the data is already imported!")
                    _logger.warning(_('Empty data'))

    def create_refund(self, data, type='out_refund'):
        company = self.env['res.company'].browse(1)
        if data:
            recs = []
            parsed_data = json.loads(str(data.text))
            count = 0
            if parsed_data:
                if type == 'out_refund':
                    get_data_for = 'RefundReceipt'

                if parsed_data.get('QueryResponse') and parsed_data.get('QueryResponse').get(get_data_for):
                    for cust in parsed_data.get('QueryResponse').get(get_data_for):
                        return_val = self.check_account_id(cust)
                        _logger.info("QB Invoice Data -----> {}".format(cust))
                        count = count + 1
                        account_invoice = self.env['account.move'].search([('qbo_invoice_id', '=', cust.get('Id'))])
                        _logger.info("ACC invoice is -----> {}".format(account_invoice))
                        if not account_invoice:
                            _logger.info("Attempting for Invoice Creation")
                            _logger.info("QBO obj is -----> {}".format(cust))
                            dict_i = self.create_invoice_dict(cust, type)
                            dict_i['invoice_line_ids'] = []
                            invoice_obj = self.env['res.partner'].search([('id', '=', dict_i.get('partner_id'))],
                                                                         limit=1)
                            invoice_line = self.odoo_create_invoice_line_dict(cust, invoice_obj, type,
                                                                              dict_i.get('qbo_invoice_id'))
                            if invoice_line:
                                for k in invoice_line:
                                    if 'exclude_from_invoice_tab' in k and not k['exclude_from_invoice_tab']:
                                        dict_i['invoice_line_ids'].append((0, 0, k))
                                    elif 'exclude_from_invoice_tab' not in k:
                                        dict_i['invoice_line_ids'].append((0, 0, k))
                                _logger.info("Dictionary for f is ---> {}".format(dict_i))
                                invoice_obj = self.env['account.move'].create(dict_i)

                                if not invoice_obj.posted_before:

                                    # invoice_obj.action_post()

                                    company.quickbooks_last_refund_imported_id = cust.get('Id')
                            else:
                                _logger.error("NO Line Found for Invoice!")
                        # else:
                        #     _logger.info("Begin updating taxes!")
                        #     account_invoice.button_draft()
                        #     for invoice_line in account_invoice.invoice_line_ids:
                        #         account_invoice.write({'invoice_line_ids': [Command.delete(invoice_line.id)]})
                        #     dict_i = {'invoice_line_ids': []}
                        #     invoice_obj = account_invoice.partner_id
                        #     invoice_line = self.odoo_create_invoice_line_dict(cust, invoice_obj, type,
                        #                                                       dict_i.get('qbo_invoice_id'))
                        #     if invoice_line:
                        #         for k in invoice_line:
                        #             if not k['exclude_from_invoice_tab']:
                        #                 if cust.get('TxnTaxDetail') and cust.get('TxnTaxDetail').get(
                        #                         'TotalTax') == 0:
                        #                     k['tax_ids'] = False
                        #                 dict_i['invoice_line_ids'].append((0, 0, k))
                        #         _logger.info("Dictionary for invoice line is ---> {}".format(dict_i))
                        #         account_invoice.write(dict_i)
                        #     account_invoice.action_post()
                        #     _logger.info("End updating taxes!")
                        #     if type == 'out_invoice':
                        #         company.quickbooks_last_invoice_imported_id = cust.get('Id')
                        #     elif type == 'out_refund':
                        #         company.quickbooks_last_credit_note_imported_id = cust.get('Id')
                        #     elif type == 'in_invoice':
                        #         company.quickbooks_last_vendor_bill_imported_id = cust.get('Id')
                        #     _logger.info("All data seems to be imported successfully!")
                else:
                    raise UserError("It seems that all of the data is already imported!")
                    _logger.warning(_('Empty data'))

    def map_payment_invoice(self):
        for record in self:
            pay_term_lines = record.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', record.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]
            if record.is_inbound():
                domain.append(('balance', '<', 0.0))
                # domain.append(('ref', '=', record.name))
            move_payment_lines = self.env['account.move.line'].search(domain)
            move_payment_lines_filtered = move_payment_lines.filtered(lambda m: m.move_id.payment_id.qbo_payment_ref == record.qbo_invoice_name)
            for line in move_payment_lines_filtered:
                record.js_assign_outstanding_line(line.id)

    def odoo_create_invoice_line_dict_discount_tax(self, cust, inv_type, qbo_inv_id=''):
        _logger.info("Attempting to add Discount Tax")
        if inv_type == 'out_invoice' or inv_type == 'out_refund':
            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                    qb_tax_id = cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value')
                    record = self.env['account.tax']
                    tax = record.search([('qbo_tax_id', '=', qb_tax_id), ('type_tax_use', '=', 'sale')])
                    if tax:
                        custom_tax_id = [[6, False, [tax.id]]]
                        _logger.info("TAX ATTACHED {}".format(tax.id))
                    else:
                        custom_tax_id = [[6, False, []]]
            else:
                custom_tax_id = [[6, False, []]]

            if cust.get('TxnTaxDetail').get('TaxLine'):
                _logger.info(_("TxnTaxDetailTxnTaxDetail %s" %
                               cust['TxnTaxDetail']['TaxLine'][0]['TaxLineDetail']['TaxRateRef']['value']))

                if cust['TxnTaxDetail']['TaxLine'][0]['TaxLineDetail']['TaxRateRef']['value']:
                    qb_tax_id = cust['TxnTaxDetail']['TaxLine'][0]['TaxLineDetail']['TaxRateRef']['value']
                    record = self.env['account.tax']
                    tax = record.search([('qbo_tax_rate_id', '=', qb_tax_id), ('type_tax_use', '=', 'sale')])
                    if tax:
                        custom_tax_id = [[6, False, [tax.id]]]
                        _logger.info("TAX ATTACHED {}".format(tax.id))
                    else:
                        custom_tax_id = [[6, False, []]]
            else:
                custom_tax_id = [[6, False, []]]
        else:
            custom_tax_id = [[6, False, []]]
        return custom_tax_id

    def odoo_create_invoice_line_dict(self, cust, invoice_obj, type,qbo_inv_id=''):
        _logger.info("Attempting to create Invoice Line Dictionary")
        inv_line_data = []
        discount = 0
        custom_discount_tax_id = False
        for i in cust.get('Line'):

            dict_ol = {}
            dict_col = {}
            dict_tol = {}
            # print("\n\nline Detail : ",i)
            if type == 'out_invoice' or type == 'out_refund':
                get_data_for = 'SalesItemLineDetail'
            else:
                get_data_for = 'ItemBasedExpenseLineDetail'

            if type == 'out_invoice' or type == 'out_refund':
                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                    if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                        qb_tax_id = cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value')
                        record = self.env['account.tax']
                        tax = record.search([('qbo_tax_id', '=', qb_tax_id), ('type_tax_use', '=', 'sale')])
                        if tax:
                            custom_tax_id = [[6, False, [tax.id]]]
                            custom_discount_tax_id = custom_tax_id
                            _logger.info(_('\n\n\n custom_tax_idcustom_tax_idcustom_tax_idcustom_tax_idcustom_tax_id %s' %custom_tax_id))
                            # [[6, False, [2]]]
                            _logger.info("TAX ATTACHED {}".format(tax.id))
                        else:
                            custom_tax_id = [[6, False, []]]
                else:
                    custom_tax_id = [[6, False, []]]

                if cust.get('TxnTaxDetail').get('TaxLine'):
                    _logger.info(_("TxnTaxDetailTxnTaxDetail %s"%cust['TxnTaxDetail']['TaxLine'][0]['TaxLineDetail']['TaxRateRef']['value']))

                    if  cust['TxnTaxDetail']['TaxLine'][0]['TaxLineDetail']['TaxRateRef']['value']:
                        qb_tax_id = cust['TxnTaxDetail']['TaxLine'][0]['TaxLineDetail']['TaxRateRef']['value']
                        record = self.env['account.tax']
                        tax = record.search([('qbo_tax_rate_id', '=', qb_tax_id), ('type_tax_use', '=', 'sale')])
                        if tax:
                            custom_tax_id = [[6, False, [tax.id]]]
                            custom_discount_tax_id = custom_tax_id
                            _logger.info(_('\n\n\n custom_tax_idcustom_tax_idcustom_tax_idcustom_tax_idcustom_tax_id %s' %custom_tax_id))
                            # [[6, False, [2]]]
                            _logger.info("TAX ATTACHED {}".format(tax.id))
                        else:
                            custom_tax_id = [[6, False, []]]
                else:
                    custom_tax_id = [[6, False, []]]
            else:
                custom_tax_id = [[6, False, []]]

            if i.get('SalesItemLineDetail'):
                if i.get('SalesItemLineDetail').get('TaxCodeRef'):
                    if i.get('SalesItemLineDetail').get('TaxCodeRef').get('value') == "TAX":

                        qb_tax_id = i.get('SalesItemLineDetail').get('TaxCodeRef').get('value')
                        record = self.env['account.tax']
                        tax = record.search([('qbo_tax_id', '=', qb_tax_id), ('type_tax_use', '=', 'sale')])

                        if tax:
                            # dict_ol['tax_ids'] = [[6, False, [tax.id]]]
                            custom_tax_id = [[6, False, [tax.id]]]
                            # [[6, False, [2]]]
                            _logger.info("TAX ATTACHED {}".format(tax.id))
                    else:
                        # dict_ol['tax_ids'] = [[6, False, []]]
                        custom_tax_id = [[6, False, []]]
                else:
                    # dict_ol['tax_ids'] = [[6, False, []]]
                    custom_tax_id = [[6, False, []]]

            else:
                dict_ol['tax_ids'] = [[6, False, []]]
            if i.get('Id') and not i.get(get_data_for) and not 'AccountBasedExpenseLineDetail' in i:
                _logger.info('\n\n AccountBasedExpenseLineDetailAccountBasedExpenseLineDetailAccountBasedExpenseLineDetailAccountBasedExpenseLineDetailAccountBasedExpenseLineDetailAccountBasedExpenseLineDetailAccountBasedExpenseLineDetailAccountBasedExpenseLineDetail\n')
                dict_ol.clear()
                dict_col.clear()
                dict_tol.clear()

                dict_ol['qb_id'] = int(i.get('Id'))


                # ---------------------------TAX--------------------------------------
                if 'TxnTaxDetail' in cust and cust.get('TxnTaxDetail'):

                    if cust.get('TxnTaxDetail').get('TaxLine'):

                        if cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail'):
                            tax_val = cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get('TaxRateRef').get('value')


                            if tax_val:
                                record = self.env['account.tax']
                                tax = record.search([('qbo_tax_rate_id', '=', tax_val)], limit=1)

                                if tax:
                                    dict_ol['tax_ids'] = [[6, False, [tax.id]]]

                            else:
                                # dict_ol['invoice_line_tax_ids'] = None
                                dict_ol['tax_ids'] = [[6, False, []]]

                            if cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get('NetAmountTaxable'):
                                dict_ol['price_unit'] = float(cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get('NetAmountTaxable'))
                            else:
                                dict_ol['price_unit'] = 0

                dict_ol['quantity'] = 1.0


                if i.get('Description'):

                    dict_ol['name'] = i.get('Description')

                else:
                    dict_ol['name'] = 'NA'

                if type=='in_invoice':
                    company = self.env['res.users'].search([('id', '=', 2)]).company_id
                    if company:
                        if company.qb_expense_account:
                            dict_ol['account_id'] = company.qb_expense_account.id
                        else:
                            raise UserError("Please set the Expense Account in QBO Configuration")

                if type == 'in_invoice':
                    company = self.env['res.users'].search([('id', '=', 2)]).company_id
                    if company:
                        if company.qb_expense_account:
                            dict_ol['account_id'] = company.qb_expense_account.id
                        else:
                            raise UserError("Please set the Expense Account in QBO Configuration")
                if type == 'out_invoice' or type=='out_refund':
                    company = self.env['res.users'].search([('id', '=', 2)]).company_id
                    if company:
                        if company.qb_income_account:
                            dict_ol['account_id'] = company.qb_income_account.id
                        else:
                            raise UserError("Please set the Income Account in QBO Configuration")

                if 'account_id' in dict_ol :
                    _logger.info("\n\n Invoice Line is  ---> {}".format(dict_ol))
                    inv_line_data.append(dict_ol)

            if 'AccountBasedExpenseLineDetail' in i and i.get('AccountBasedExpenseLineDetail'):
                # res_account = self.env['account.account'].search(
                #     [('name', '=', i.get('AccountBasedExpenseLineDetail').get('AccountRef').get('name'))])
                res_account_id = self.env['account.account'].get_account_ref(i.get('AccountBasedExpenseLineDetail').get('AccountRef').get('value'))
                res_account = self.env['account.account'].browse(res_account_id)
                _logger.info(_('\n\n=============== AccountBasedExpenseLineDetailAccountBasedExpenseLineDetailAccountBasedExpenseLineDetail %s'% res_account))
                if not res_account:
                    raise UserError('Account QBO ID '+i.get('AccountBasedExpenseLineDetail').get('AccountRef').get('value')+' doesnot exists in Odoo. ')
                if res_account:

                    dict_ol.clear()
                    dict_col.clear()
                    dict_tol.clear()

                    # Move Id for Product Line & Customer Account Receivable Line
                    # dict_ol['move_id'] = invoice_obj.id
                    # dict_col['move_id'] = invoice_obj.id
                    # dict_tol['move_id'] = invoice_obj.id

                    # Product Id for Product Line & Customer Account Receivable Line
                    #                     dict_ol['product_id'] = res_product.id
                    #                     dict_col['product_id'] = False
                    #                     dict_tol['product_id'] = False

                    # Parent Id for Product Line & Customer Account Receivable Line
                    dict_ol['partner_id'] = invoice_obj.id
                    dict_col['partner_id'] = invoice_obj.id
                    dict_tol['partner_id'] = invoice_obj.id

                    # Exclude Receivable from Invoice Tab
                    dict_ol['exclude_from_invoice_tab'] = False
                    dict_col['exclude_from_invoice_tab'] = True
                    dict_tol['exclude_from_invoice_tab'] = True

                    # Quickbooks Id for Product Line & Customer Account Receivable Line
                    if i.get('Id'):
                        dict_ol['qb_id'] = int(i.get('Id'))
                        dict_col['qb_id'] = int(i.get('Id'))
                        dict_tol['qb_id'] = int(i.get('Id'))

                    # ---------------------------TAX--------------------------------------
                    if i.get('AccountBasedExpenseLineDetail').get('TaxCodeRef'):
                        tax_val = i.get('AccountBasedExpenseLineDetail').get('TaxCodeRef').get('value')
                        tax=''
                        if type == 'in_invoice':

                            record = self.env['account.tax']
                            tax = record.search([('qbo_tax_id', '=', tax_val), ('type_tax_use', '=', 'purchase')], limit=1)

                        else:

                            record = self.env['account.tax']
                            tax = record.search([('qbo_tax_id', '=', tax_val), ('type_tax_use', '=', 'sale')],
                                                    limit=1)

                        if tax:
                            dict_ol['tax_ids'] = [[6, False, [tax.id]]]

                        else:
                            # dict_ol['invoice_line_tax_ids'] = None
                            dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]

                    if i.get('AccountBasedExpenseLineDetail').get('Qty'):
                        dict_ol['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')
                        dict_col['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')
                        dict_tol['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')

                    else:
                        dict_ol['quantity'] = 1.0
                        dict_col['quantity'] = 1.0
                        dict_tol['quantity'] = 1.0

                    if i.get('AccountBasedExpenseLineDetail').get('UnitPrice'):
                        dict_ol['price_unit'] = float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice'))
                        dict_col['price_unit'] = -(float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice')))

                        dict_ol['credit'] = abs(
                            dict_ol['quantity'] * float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice')))
                        dict_ol['debit'] = 0

                        dict_col['credit'] = 0
                        dict_col['debit'] = abs(
                            dict_col['quantity'] * float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice')))

                    else:
                        if not i.get('AccountBasedExpenseLineDetail').get('Qty'):
                            dict_ol['price_unit'] = float(i.get('Amount'))
                            dict_col['price_unit'] = -(float(i.get('Amount')))

                            dict_ol['credit'] = abs(dict_ol['quantity'] * float(i.get('Amount')))
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = abs(dict_col['quantity'] * float(i.get('Amount')))
                        else:
                            dict_ol['price_unit'] = 0
                            dict_col['price_unit'] = 0

                            dict_ol['credit'] = 0
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = 0

                    if i.get('Description'):
                        dict_ol['name'] = i.get('Description')
                        dict_col['name'] = i.get('Description')
                        dict_tol['name'] = i.get('Description')
                    else:
                        dict_ol['name'] = 'NA'
                        dict_col['name'] = 'NA'
                        dict_tol['name'] = 'NA'

                    if type == 'out_invoice' or type == 'out_refund':
                        if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                tax_amount = cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get(
                                    'TaxPercent')
                                dict_tol['price_unit'] = float(
                                    dict_ol['quantity'] * dict_ol['price_unit'] * float(tax_amount / 100))
                                dict_tol['credit'] = abs(dict_tol['price_unit'])
                                dict_tol['debit'] = 0

                                dict_col['debit'] += abs(dict_tol['credit'])
                            else:
                                dict_tol['price_unit'] = 0
                                dict_tol['credit'] = 0
                                dict_tol['debit'] = 0

                        else:
                            dict_tol['price_unit'] = 0
                            dict_tol['credit'] = 0
                            dict_tol['debit'] = 0
                    else:
                        dict_tol['price_unit'] = 0
                        dict_tol['credit'] = 0
                        dict_tol['debit'] = 0



                    if type == 'out_refund' or type == 'in_invoice':
                        dict_ol['credit'], dict_ol['debit'] = dict_ol['debit'], dict_ol['credit']
                        dict_col['credit'], dict_col['debit'] = dict_col['debit'], dict_col['credit']
                        dict_tol['credit'], dict_tol['debit'] = dict_tol['debit'], dict_tol['credit']

                    if res_account:
                        dict_ol['account_id'] = res_account.id
                        _logger.info("PRODUCT has income account set")

                    if type=="in_invoice":
                        if invoice_obj.property_account_payable_id:
                            dict_col['account_id'] = invoice_obj.property_account_payable_id.id
                            dict_tol['account_id'] = invoice_obj.property_account_payable_id.id
                            company = self.env['res.users'].search([('id', '=', 2)]).company_id
                            if invoice_obj.property_account_payable_id.company_id != company:
                                account_company = self.env['account.account'].sudo().search([('code', '=', invoice_obj.property_account_payable_id.code), ('company_id', '=', company.id)])
                                dict_col['account_id'] = account_company.id
                                dict_tol['account_id'] = account_company.id

                    if type=="out_invoice" or type=="out_refund":
                        if invoice_obj.property_account_receivable_id:
                            dict_col['account_id'] = invoice_obj.property_account_receivable_id.id
                            dict_tol['account_id'] = invoice_obj.property_account_receivable_id.id
                            company = self.env['res.users'].search([('id', '=', 2)]).company_id
                            if invoice_obj.property_account_receivable_id.company_id != company:
                                account_company = self.env['account.account'].sudo().search(
                                    [('code', '=', invoice_obj.property_account_receivable_id.code),
                                     ('company_id', '=', company.id)])
                                dict_col['account_id'] = account_company.id
                                dict_tol['account_id'] = account_company.id
                    # if invoice_obj.property_account_receivable_id:
                    #     dict_col['account_id'] = invoice_obj.property_account_receivable_id.id
                    #     dict_tol['account_id'] = invoice_obj.property_account_receivable_id.id

                    if 'account_id' in dict_ol and 'account_id' in dict_col:
                        _logger.info("\n\n Invoice Line is  ---> {}".format(dict_ol))
                        inv_line_data.append(dict_ol)
                        inv_line_data.append(dict_col)
                        if type == 'out_invoice' or type == 'out_refund':
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                                dict_ol['tax_repartition_line_id'] = False
                                dict_col['tax_repartition_line_id'] = False
                                #
                                #                                 tax_repartition_line_id = self.env['account.tax.repartition.line'].search([('repartition_type', '=', 'tax')],limit=1)
                                dict_tol['tax_repartition_line_id'] = False
                                #                                 dict_tol['tax_repartition_line_id'] = tax_repartition_line_id.id

                                dict_ol['tax_base_amount'] = 0
                                dict_col['tax_base_amount'] = 0
                                dict_tol['tax_base_amount'] = dict_ol['quantity'] * dict_ol['price_unit']

                                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                    inv_line_data.append(dict_tol)

            if i.get(get_data_for):
                # print('\n\n 8888888888888888888888888888888888888888888888888888888',i,i.get(get_data_for))

                qbo_id = i.get(get_data_for).get('ItemRef').get('value')
                res_product = self.env['product.product'].search(
                    [('default_code', '=', i.get(get_data_for).get('ItemRef').get('name').split(' -')[0])])
                if not res_product:
                    res_product = self.env['product.product'].search(
                        [('qbo_product_id', '=', i.get(get_data_for).get('ItemRef').get('value'))])
                # print('res_product : ',res_product,isinstance(qbo_id, int))
                if not res_product:
                    if not isinstance(qbo_id, int):
                        vals = {
                            'name': i.get('Description') or i.get(get_data_for).get('ItemRef').get('name'),
                            'type': 'service',
                            'qbo_product_id': qbo_id,
                        }
                        res_product=self.env['product.product'].create(vals)

                if res_product:

                    dict_ol.clear()
                    dict_col.clear()
                    dict_tol.clear()

                    # Move Id for Product Line & Customer Account Receivable Line
                    # dict_ol['move_id'] = invoice_obj.id
                    # dict_col['move_id'] = invoice_obj.id
                    # dict_tol['move_id'] = invoice_obj.id

                    # Product Id for Product Line & Customer Account Receivable Line
                    dict_ol['product_id'] = res_product.id
                    dict_col['product_id'] = False
                    dict_tol['product_id'] = False

                    # Parent Id for Product Line & Customer Account Receivable Line
                    dict_ol['partner_id'] = invoice_obj.id
                    dict_col['partner_id'] = invoice_obj.id
                    dict_tol['partner_id'] = invoice_obj.id

                    # Exclude Receivable from Invoice Tab
                    dict_ol['exclude_from_invoice_tab'] = False
                    dict_col['exclude_from_invoice_tab'] = True
                    dict_tol['exclude_from_invoice_tab'] = True

                    # Quickbooks Id for Product Line & Customer Account Receivable Line
                    if i.get('Id'):
                        dict_ol['qb_id'] = int(i.get('Id'))
                        dict_col['qb_id'] = int(i.get('Id'))
                        dict_tol['qb_id'] = int(i.get('Id'))

                    # ---------------------------TAX--------------------------------------
                    if i.get(get_data_for).get('TaxCodeRef'):
                        # print(" Odoo custom tax id!!!!!!!!!!!!!!!!!!!!!!!!", custom_tax_id)

                        tax_val = i.get(get_data_for).get('TaxCodeRef').get('value')
                        if tax_val:
                            #                             dict_ol['invoice_line_tax_ids'] = custom_tax_id
                            dict_ol['tax_ids'] = custom_tax_id
                            # print("custom tax id!!!!!!!!!!!!!!!!!!!!!!!!",custom_tax_id)
                            #                             dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = custom_tax_id
                            dict_tol['tax_ids'] = custom_tax_id
                        else:
                            # dict_ol['invoice_line_tax_ids'] = None
                            dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]

                    if i.get(get_data_for).get('Qty'):
                        dict_ol['quantity'] = i.get(get_data_for).get('Qty')
                        dict_col['quantity'] = i.get(get_data_for).get('Qty')
                        dict_tol['quantity'] = i.get(get_data_for).get('Qty')
                    else:
                        dict_ol['quantity'] = 0
                        dict_col['quantity'] = 0
                        dict_tol['quantity'] = 0

                    if i.get(get_data_for).get('UnitPrice'):
                        dict_ol['price_unit'] = float(i.get(get_data_for).get('UnitPrice'))
                        dict_col['price_unit'] = -(float(i.get(get_data_for).get('UnitPrice')))

                        dict_ol['credit'] = abs(dict_ol['quantity'] * float(i.get(get_data_for).get('UnitPrice')))
                        dict_ol['debit'] = 0

                        dict_col['credit'] = 0
                        dict_col['debit'] = abs(dict_col['quantity'] * float(i.get(get_data_for).get('UnitPrice')))

                    else:
                        if not i.get(get_data_for).get('Qty'):
                            dict_ol['price_unit'] = float(i.get('Amount'))
                            dict_col['price_unit'] = -(float(i.get('Amount')))

                            dict_ol['credit'] = abs(dict_ol['quantity'] * float(i.get('Amount')))
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = abs(dict_col['quantity'] * float(i.get('Amount')))
                        else:
                            dict_ol['price_unit'] = 0
                            dict_col['price_unit'] = 0

                            dict_ol['credit'] = 0
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = 0

                    if i.get('Description'):
                        dict_ol['name'] = i.get('Description')
                        dict_col['name'] = i.get('Description')
                        dict_tol['name'] = i.get('Description')
                    else:
                        dict_ol['name'] = 'NA'
                        dict_col['name'] = 'NA'
                        dict_tol['name'] = 'NA'

                    if type == 'out_invoice' or type == 'out_refund':
                        if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                tax_amount = cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get(
                                    'TaxPercent')
                                dict_tol['price_unit'] = float(
                                    dict_ol['quantity'] * dict_ol['price_unit'] * float(tax_amount / 100))
                                dict_tol['credit'] = abs(dict_tol['price_unit'])
                                dict_tol['debit'] = 0

                                dict_col['debit'] += abs(dict_tol['credit'])
                            else:
                                dict_tol['price_unit'] = 0
                                dict_tol['credit'] = 0
                                dict_tol['debit'] = 0

                        else:
                            dict_tol['price_unit'] = 0
                            dict_tol['credit'] = 0
                            dict_tol['debit'] = 0
                    else:
                        dict_tol['price_unit'] = 0
                        dict_tol['credit'] = 0
                        dict_tol['debit'] = 0

                    if type == 'out_refund' or type == 'in_invoice':
                        dict_ol['credit'], dict_ol['debit'] = dict_ol['debit'], dict_ol['credit']
                        dict_col['credit'], dict_col['debit'] = dict_col['debit'], dict_col['credit']
                        dict_tol['credit'], dict_tol['debit'] = dict_tol['debit'], dict_tol['credit']

                    if res_product.property_account_income_id:
                        dict_ol['account_id'] = res_product.property_account_income_id.id
                        company = self.env['res.users'].search([('id', '=', 2)]).company_id
                        if res_product.property_account_income_id.company_id != company:
                            account_company = self.env['account.account'].sudo().search(
                                [('code', '=', res_product.property_account_income_id.code),
                                 ('company_id', '=', company.id)])
                            dict_ol['account_id'] = account_company.id
                        _logger.info("PRODUCT has income account set")
                    else:
                        dict_ol['account_id'] = res_product.categ_id.property_account_income_categ_id.id
                        company = self.env['res.users'].search([('id', '=', 2)]).company_id
                        if res_product.categ_id.property_account_income_categ_id.company_id != company:
                            account_company = self.env['account.account'].sudo().search(
                                [('code', '=', res_product.categ_id.property_account_income_categ_id.code),
                                 ('company_id', '=', company.id)])
                            dict_ol['account_id'] = account_company.id
                        _logger.info("No Income account was set, taking from product category..")
                    #
                    # if invoice_obj.property_account_receivable_id:
                    #     dict_col['account_id'] = invoice_obj.property_account_receivable_id.id
                    #     dict_tol['account_id'] = invoice_obj.property_account_receivable_id.id
                    if type=="in_invoice":
                        if invoice_obj.property_account_payable_id:
                            dict_col['account_id'] = invoice_obj.property_account_payable_id.id
                            dict_tol['account_id'] = invoice_obj.property_account_payable_id.id
                            company = self.env['res.users'].search([('id', '=', 2)]).company_id
                            if invoice_obj.property_account_payable_id.company_id != company:
                                account_company = self.env['account.account'].sudo().search(
                                    [('code', '=', invoice_obj.property_account_payable_id.code),
                                     ('company_id', '=', company.id)])
                                dict_col['account_id'] = account_company.id
                                dict_tol['account_id'] = account_company.id

                    if type=="out_invoice" or type=="out_refund":
                        if invoice_obj.property_account_receivable_id:
                            dict_col['account_id'] = invoice_obj.property_account_receivable_id.id
                            dict_tol['account_id'] = invoice_obj.property_account_receivable_id.id
                            company = self.env['res.users'].search([('id', '=', 2)]).company_id
                            if invoice_obj.property_account_receivable_id.company_id != company:
                                account_company = self.env['account.account'].sudo().search(
                                    [('code', '=', invoice_obj.property_account_receivable_id.code),
                                     ('company_id', '=', company.id)])
                                dict_col['account_id'] = account_company.id
                                dict_tol['account_id'] = account_company.id
                    # else:
                    #     raise UserError("Accounts Receivable/Payable not set for Customer ---> {}".format(invoice_obj.name))
                    #     _logger.info("No Property Account Receivable Set!")

                    _logger.info("DICT COL IS ---> {}".format(dict_col))
                    _logger.info("DICT OL IS ---> {}".format(dict_ol))
                    _logger.info("DICT TOL IS ---> {}".format(dict_tol))
                    if 'account_id' in dict_ol and 'account_id' in dict_col:
                        _logger.info("\n\n Invoice Line is  ---> {}".format(dict_ol))
                        # dict_ol['discount'] = discount
                        dict_ol['currency_id'] = self.env.user.company_id.currency_id.id
                        inv_line_data.append(dict_ol)

                        # dict_col['discount'] = discount
                        dict_col['currency_id'] = self.env.user.company_id.currency_id.id
                        inv_line_data.append(dict_col)
                        _logger.info("INVOICE LINE DATA FOR NOW IS ---> {}".format(inv_line_data))
                        if type == 'out_invoice' or type == 'out_refund':
                            _logger.info("Getting Additional Details!")
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                                _logger.info("Getting Transaction Details!")
                                dict_ol['tax_repartition_line_id'] = False
                                dict_col['tax_repartition_line_id'] = False

                                #                                 tax_repartition_line_id = self.env['account.tax.repartition.line'].search([('repartition_type', '=', 'tax')],limit=1)
                                # #                                 dict_tol['tax_repartition_line_id'] = tax_repartition_line_id.id
                                dict_tol['tax_repartition_line_id'] = False
                                dict_ol['tax_base_amount'] = 0
                                dict_col['tax_base_amount'] = 0
                                dict_tol['tax_base_amount'] = dict_ol['quantity'] * dict_ol['price_unit']
                                # dict_tol['discount'] = discount
                                dict_tol['currency_id'] = self.env.user.company_id.currency_id.id



                                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                    inv_line_data.append(dict_tol)
                                else:
                                    _logger.info("TAX Code Reference Value Not Found!")
                    else:
                        _logger.info("Account ID not found in the dictionary!")
                else:
                    raise UserError('Product ' + str(
                        i.get(get_data_for).get('ItemRef').get(
                            'name')) + ' is not defined in Odoo. Invoice type '+str(type)+' Name :' + cust.get(
                        'DocNumber'))






        _logger.info("INVOICE LINE DATA SENDING FOR CREATION IS --BEFORE -> {}".format(inv_line_data))
        for j in inv_line_data:

            if j.get('credit') and j.get('debit'):
                del j['credit']
                del j['debit']
            if 'product_id' in j:
                if j.get('quantity')==0:
                    j['quantity']=1
                if not j.get('product_id'):
                    inv_line_data.remove(j)

        # Create discount line
        invoice_lines = cust.get('Line')
        dict_discount = {}
        if invoice_lines:
            for j in invoice_lines:
                if "DiscountLineDetail" in j:
                    if j.get('DiscountLineDetail').get('PercentBased'):
                        if j.get("DiscountLineDetail").get('DiscountPercent'):
                            raise UserError("This invoice has Discount Percentage")
                            # res_account = self.env['account.account'].search(
                            #     [('qbo_id', '=', j.get('DiscountLineDetail').get('DiscountAccountRef').get('value'))])
                            # discount = j.get('`DiscountLineDetail`').get('DiscountPercent')
                    else:
                        dict_discount['name'] = 'Discount'
                        res_account = self.env['account.account'].search(
                            [('code', '=', j.get('DiscountLineDetail').get('DiscountAccountRef').get('name').split(' ')[0])])
                        if not res_account:
                            raise UserError("Can not find account: " + j.get('DiscountLineDetail').get('DiscountAccountRef').get('name'))
                        dict_discount['account_id'] = res_account.id
                        dict_discount['exclude_from_invoice_tab'] = False
                        dict_discount['quantity'] = 1
                        dict_discount['price_unit'] = -j.get('Amount')
                        if custom_discount_tax_id:
                            dict_discount['tax_ids'] = custom_discount_tax_id
                        inv_line_data.append(dict_discount)
        _logger.info("INVOICE LINE DATA SENDING FOR CREATION IS --LATER -> {}".format(inv_line_data))

        return inv_line_data


    def create_invoice_line_dict(self, cust, invoice_obj, type):
        _logger.info("Attempting to create Invoice Line Dictionary")
        inv_line_data = []
        for i in cust.get('Line'):
            dict_ol = {}
            dict_col = {}
            dict_tol = {}

            if type == 'out_invoice' or type == 'out_refund':
                get_data_for = 'SalesItemLineDetail'
            else:
                get_data_for = 'ItemBasedExpenseLineDetail'

            if type == 'out_invoice' or type == 'out_refund':
                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                    if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):

                        qb_tax_id = cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value')
                        record = self.env['account.tax']
                        tax = record.search([('qbo_tax_id', '=', qb_tax_id)])
                        if tax:
                            custom_tax_id = [[6, False, [tax.id]]]
                            # [[6, False, [2]]]
                            _logger.info("TAX ATTACHED {}".format(tax.id))
                        else:
                            custom_tax_id = [[6, False, []]]
                else:
                    custom_tax_id = [[6, False, []]]
            else:
                custom_tax_id = [[6, False, []]]


            if 'AccountBasedExpenseLineDetail' in i and i.get('AccountBasedExpenseLineDetail'):
                res_account_id = self.env['account.account'].get_account_ref(i.get('AccountBasedExpenseLineDetail').get('AccountRef').get('value'))
                res_account = self.env['account.account'].browse(res_account_id)
                if not res_account:
                    raise UserError('Account QBO ID '+i.get('AccountBasedExpenseLineDetail').get('AccountRef').get('value')+' doesnot exists in Odoo. ')
                if res_account:

                    dict_ol.clear()
                    dict_col.clear()
                    dict_tol.clear()

                    # Move Id for Product Line & Customer Account Receivable Line
                    dict_ol['move_id'] = invoice_obj.id
                    dict_col['move_id'] = invoice_obj.id
                    dict_tol['move_id'] = invoice_obj.id

                    # Product Id for Product Line & Customer Account Receivable Line
#                     dict_ol['product_id'] = res_product.id
#                     dict_col['product_id'] = False
#                     dict_tol['product_id'] = False

                    # Parent Id for Product Line & Customer Account Receivable Line
                    dict_ol['partner_id'] = invoice_obj.partner_id.id
                    dict_col['partner_id'] = invoice_obj.partner_id.id
                    dict_tol['partner_id'] = invoice_obj.partner_id.id

                    # Exclude Receivable from Invoice Tab
                    dict_ol['exclude_from_invoice_tab'] = False
                    dict_col['exclude_from_invoice_tab'] = True
                    dict_tol['exclude_from_invoice_tab'] = True

                    # Quickbooks Id for Product Line & Customer Account Receivable Line
                    if i.get('Id'):
                        dict_ol['qb_id'] = int(i.get('Id'))
                        dict_col['qb_id'] = int(i.get('Id'))
                        dict_tol['qb_id'] = int(i.get('Id'))

                    # ---------------------------TAX--------------------------------------
                    if i.get('AccountBasedExpenseLineDetail').get('TaxCodeRef'):
                        tax_val = i.get('AccountBasedExpenseLineDetail').get('TaxCodeRef').get('value')
                        if tax_val == 'TAX':
                            dict_ol['tax_ids'] = custom_tax_id
#                             print("CUSTOM TAX ID IS -----------",custom_tax_id)
#                             dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]
                        else:
                            # dict_ol['invoice_line_tax_ids'] = None
                            dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]


                    if i.get('AccountBasedExpenseLineDetail').get('Qty'):
                        dict_ol['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')
                        dict_col['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')
                        dict_tol['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')

                    else:
                        dict_ol['quantity'] = 1.0
                        dict_col['quantity'] = 1.0
                        dict_tol['quantity'] = 1.0

                    if i.get('AccountBasedExpenseLineDetail').get('UnitPrice'):
                        dict_ol['price_unit'] = float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice'))
                        dict_col['price_unit'] = -(float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice')))

                        dict_ol['credit'] = dict_ol['quantity'] * float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice'))
                        dict_ol['debit'] = 0

                        dict_col['credit'] = 0
                        dict_col['debit'] = dict_col['quantity'] * float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice'))

                    else:
                        if not i.get('AccountBasedExpenseLineDetail').get('Qty'):
                            dict_ol['price_unit'] = float(i.get('Amount'))
                            dict_col['price_unit'] = -(float(i.get('Amount')))

                            dict_ol['credit'] = dict_ol['quantity'] * float(i.get('Amount'))
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = dict_col['quantity'] * float(i.get('Amount'))
                        else:
                            dict_ol['price_unit'] = 0
                            dict_col['price_unit'] = 0

                            dict_ol['credit'] = 0
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = 0

                    if i.get('Description'):
                        dict_ol['name'] = i.get('Description')
                        dict_col['name'] = i.get('Description')
                        dict_tol['name'] = i.get('Description')
                    else:
                        dict_ol['name'] = 'NA'
                        dict_col['name'] = 'NA'
                        dict_tol['name'] = 'NA'

                    if type == 'out_invoice' or type == 'out_refund':
                        if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                tax_amount = cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get('TaxPercent')
                                dict_tol['price_unit'] = float(dict_ol['quantity'] * dict_ol['price_unit'] * float(tax_amount/100))
                                dict_tol['credit'] = dict_tol['price_unit']
                                dict_tol['debit'] = 0

                                dict_col['debit'] += dict_tol['credit']
                            else:
                                dict_tol['price_unit'] = 0
                                dict_tol['credit'] = 0
                                dict_tol['debit'] = 0

                        else:
                            dict_tol['price_unit'] = 0
                            dict_tol['credit'] = 0
                            dict_tol['debit'] = 0
                    else:
                        dict_tol['price_unit'] = 0
                        dict_tol['credit'] = 0
                        dict_tol['debit'] = 0

                    if type == 'out_refund' or type == 'in_invoice':
                        dict_ol['credit'],dict_ol['debit'] = dict_ol['debit'],dict_ol['credit']
                        dict_col['credit'],dict_col['debit'] = dict_col['debit'],dict_col['credit']
                        dict_tol['credit'],dict_tol['debit'] = dict_tol['debit'],dict_tol['credit']

                    if res_account:
                        dict_ol['account_id'] = res_account.id
                        _logger.info("PRODUCT has income account set")

                    if invoice_obj.partner_id.property_account_receivable_id:
                        dict_col['account_id'] = invoice_obj.partner_id.property_account_receivable_id.id
                        dict_tol['account_id'] = invoice_obj.partner_id.property_account_receivable_id.id

                    if 'account_id' in dict_ol and 'account_id' in dict_col:
                        _logger.info("\n\n Invoice Line is  ---> {}".format(dict_ol))
                        inv_line_data.append(dict_ol)
                        inv_line_data.append(dict_col)
                        if type == 'out_invoice' or type == 'out_refund':
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                                dict_ol['tax_repartition_line_id'] = False
                                dict_col['tax_repartition_line_id'] = False
#
#                                 tax_repartition_line_id = self.env['account.tax.repartition.line'].search([('repartition_type', '=', 'tax')],limit=1)
                                dict_tol['tax_repartition_line_id'] = False
#                                 dict_tol['tax_repartition_line_id'] = tax_repartition_line_id.id

                                dict_ol['tax_base_amount'] = 0
                                dict_col['tax_base_amount'] = 0
                                dict_tol['tax_base_amount'] = dict_ol['quantity'] * dict_ol['price_unit']

                                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                    inv_line_data.append(dict_tol)


            if i.get(get_data_for):
                res_product = self.env['product.product'].search([('qbo_product_id', '=', i.get(get_data_for).get('ItemRef').get('value'))])
                if res_product:

                    dict_ol.clear()
                    dict_col.clear()
                    dict_tol.clear()

                    # Move Id for Product Line & Customer Account Receivable Line
                    dict_ol['move_id'] = invoice_obj.id
                    dict_col['move_id'] = invoice_obj.id
                    dict_tol['move_id'] = invoice_obj.id

                    # Product Id for Product Line & Customer Account Receivable Line
                    dict_ol['product_id'] = res_product.id
                    dict_col['product_id'] = False
                    dict_tol['product_id'] = False

                    # Parent Id for Product Line & Customer Account Receivable Line
                    dict_ol['partner_id'] = invoice_obj.partner_id.id
                    dict_col['partner_id'] = invoice_obj.partner_id.id
                    dict_tol['partner_id'] = invoice_obj.partner_id.id

                    # Exclude Receivable from Invoice Tab
                    dict_ol['exclude_from_invoice_tab'] = False
                    dict_col['exclude_from_invoice_tab'] = True
                    dict_tol['exclude_from_invoice_tab'] = True

                    # Quickbooks Id for Product Line & Customer Account Receivable Line
                    if i.get('Id'):
                        dict_ol['qb_id'] = int(i.get('Id'))
                        dict_col['qb_id'] = int(i.get('Id'))
                        dict_tol['qb_id'] = int(i.get('Id'))

                    # ---------------------------TAX--------------------------------------
                    if i.get(get_data_for).get('TaxCodeRef'):
                        tax_val = i.get(get_data_for).get('TaxCodeRef').get('value')
                        if tax_val == 'TAX':
#                             dict_ol['invoice_line_tax_ids'] = custom_tax_id
                            dict_ol['tax_ids'] = custom_tax_id
#                             print("custom tax id!!!!!!!!!!!!!!!!!!!!!!!!",custom_tax_id)
#                             dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]
                        else:
                            # dict_ol['invoice_line_tax_ids'] = None
                            dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]

                    if i.get(get_data_for).get('Qty'):
                        dict_ol['quantity'] = i.get(get_data_for).get('Qty')
                        dict_col['quantity'] = i.get(get_data_for).get('Qty')
                        dict_tol['quantity'] = i.get(get_data_for).get('Qty')

                    else:
                        dict_ol['quantity'] = 0
                        dict_col['quantity'] = 0
                        dict_tol['quantity'] = 0

                    if i.get(get_data_for).get('UnitPrice'):
                        dict_ol['price_unit'] = float(i.get(get_data_for).get('UnitPrice'))
                        dict_col['price_unit'] = -(float(i.get(get_data_for).get('UnitPrice')))

                        dict_ol['credit'] = dict_ol['quantity'] * float(i.get(get_data_for).get('UnitPrice'))
                        dict_ol['debit'] = 0

                        dict_col['credit'] = 0
                        dict_col['debit'] = dict_col['quantity'] * float(i.get(get_data_for).get('UnitPrice'))

                    else:
                        if not i.get(get_data_for).get('Qty'):
                            dict_ol['price_unit'] = float(i.get('Amount'))
                            dict_col['price_unit'] = -(float(i.get('Amount')))

                            dict_ol['credit'] = dict_ol['quantity'] * float(i.get('Amount'))
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = dict_col['quantity'] * float(i.get('Amount'))
                        else:
                            dict_ol['price_unit'] = 0
                            dict_col['price_unit'] = 0

                            dict_ol['credit'] = 0
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = 0

                    if i.get('Description'):
                        dict_ol['name'] = i.get('Description')
                        dict_col['name'] = i.get('Description')
                        dict_tol['name'] = i.get('Description')
                    else:
                        dict_ol['name'] = 'NA'
                        dict_col['name'] = 'NA'
                        dict_tol['name'] = 'NA'

                    if type == 'out_invoice' or type == 'out_refund':
                        if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                tax_amount = cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get('TaxPercent')
                                dict_tol['price_unit'] = float(dict_ol['quantity'] * dict_ol['price_unit'] * float(tax_amount/100))
                                dict_tol['credit'] = dict_tol['price_unit']
                                dict_tol['debit'] = 0

                                dict_col['debit'] += dict_tol['credit']
                            else:
                                dict_tol['price_unit'] = 0
                                dict_tol['credit'] = 0
                                dict_tol['debit'] = 0

                        else:
                            dict_tol['price_unit'] = 0
                            dict_tol['credit'] = 0
                            dict_tol['debit'] = 0
                    else:
                        dict_tol['price_unit'] = 0
                        dict_tol['credit'] = 0
                        dict_tol['debit'] = 0

                    if type == 'out_refund' or type == 'in_invoice':
                        dict_ol['credit'],dict_ol['debit'] = dict_ol['debit'],dict_ol['credit']
                        dict_col['credit'],dict_col['debit'] = dict_col['debit'],dict_col['credit']
                        dict_tol['credit'],dict_tol['debit'] = dict_tol['debit'],dict_tol['credit']

                    if res_product.property_account_income_id:
                        dict_ol['account_id'] = res_product.property_account_income_id.id
                        _logger.info("PRODUCT has income account set")
                    else:
                        dict_ol['account_id'] = res_product.categ_id.property_account_income_categ_id.id
                        _logger.info("No Income account was set, taking from product category..")

                    if invoice_obj.partner_id.property_account_receivable_id:
                        dict_col['account_id'] = invoice_obj.partner_id.property_account_receivable_id.id
                        dict_tol['account_id'] = invoice_obj.partner_id.property_account_receivable_id.id
                    else:
                        raise UserError("Account Receivable not set for Customer ---> {}".format(invoice_obj.partner_id.name))
                        _logger.info("No Property Account Receivable Set!")

                    _logger.info("DICT COL IS ---> {}".format(dict_col))
                    _logger.info("DICT OL IS ---> {}".format(dict_ol))
                    _logger.info("DICT TOL IS ---> {}".format(dict_tol))
                    if 'account_id' in dict_ol and 'account_id' in dict_col:
                        _logger.info("\n\n Invoice Line is  ---> {}".format(dict_ol))
                        inv_line_data.append(dict_ol)
                        inv_line_data.append(dict_col)
                        _logger.info("INVOICE LINE DATA FOR NOW IS ---> {}".format(inv_line_data))
                        if type == 'out_invoice' or type == 'out_refund':
                            _logger.info("Getting Additional Details!")
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                                _logger.info("Getting Transaction Details!")
                                dict_ol['tax_repartition_line_id'] = False
                                dict_col['tax_repartition_line_id'] = False

#                                 tax_repartition_line_id = self.env['account.tax.repartition.line'].search([('repartition_type', '=', 'tax')],limit=1)
# #                                 dict_tol['tax_repartition_line_id'] = tax_repartition_line_id.id
                                dict_tol['tax_repartition_line_id'] = False
                                dict_ol['tax_base_amount'] = 0
                                dict_col['tax_base_amount'] = 0
                                dict_tol['tax_base_amount'] = dict_ol['quantity'] * dict_ol['price_unit']

                                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                    inv_line_data.append(dict_tol)
                                else:
                                    _logger.info("TAX Code Reference Value Not Found!")
                    else:
                        _logger.info("Account ID not found in the dictionary!")
        _logger.info("INVOICE LINE DATA SENDING FOR CREATION IS ---> {}".format(inv_line_data))
        return inv_line_data


    @api.model
    def _prepare_invoice_export_line_dict(self, line):
        #         line = self
        company = self.env['res.users'].search([('id', '=', 2)]).company_id
        vals = {
            'Description': line.name,
            'Amount': line.price_subtotal,
        }
        # if self.partner_id.supplier_rank:
        #     if line.tax_ids:
        #         raise UserError("Taxable vendor bill cannot be exported.")

        unit_price = line.price_unit
        #  When discount is available in sale order
        if line.discount > 0:
            unit_price = line.price_unit - (line.price_unit * (line.discount / 100))
            # vals.update({'Amount': unit_price * line.product_uom_qty})
            vals.update({'Amount': unit_price * line.quantity})

        if line.tax_ids:
            taxCodeRef = 'TAX'
        else:
            taxCodeRef = 'NON'

        if self.partner_id.customer_rank:
            vals.update({
                'DetailType': 'SalesItemLineDetail',
                'SalesItemLineDetail': {
                    'ItemRef': {'value': self.env['product.template'].get_qbo_product_ref(line.product_id)},
                    'TaxCodeRef': {'value': taxCodeRef},
                    'UnitPrice': unit_price, # line.price_unit
                    'Qty': line.quantity,
                }
            })

        elif self.partner_id.supplier_rank:
            vals.update({
                'DetailType': 'ItemBasedExpenseLineDetail',
                'ItemBasedExpenseLineDetail': {
                    'ItemRef': {'value': self.env['product.template'].get_qbo_product_ref(line.product_id)},
                    'TaxCodeRef': {'value': taxCodeRef},
                    'UnitPrice': line.price_unit,
                    'Qty': line.quantity,
                    #                     'BillableStatus' : 'Billable',
                }
            })

        return vals
    
    
    @api.model
    def get_linked_sales_order_ref(self,quickbook_id):
        qbo_id = str(quickbook_id)
        company = self.env['res.users'].search([('id', '=', 2)]).company_id
        url_str = company.get_import_query_url()
        url = url_str.get('url') + '/estimate/' + qbo_id + '?minorversion=' + url_str.get('minorversion')
        result = requests.request('GET', url, headers=url_str.get('headers'))
        if result.status_code == 200 :
            return True
        else:
            return False

    @api.model
    def _prepare_invoice_export_dict(self):
        invoice = self
        vals = {

            'TxnDate': str(invoice.invoice_date),
            'DueDate': str(invoice.invoice_date_due),
        }
        
        #Added code for linking of Sales Order to an invoice
        if invoice.invoice_origin:
            _logger.info("INVOICE HAS A SALES ORDER ASSOCIATED WITH IT---> {}".format(invoice.invoice_origin))
            #Search for the related sales order
            linked_sales_order = self.env['sale.order'].search([('name','=',invoice.invoice_origin)], limit=1)
            _logger.info("LINKED SALES ORDER IS ---> {}".format(linked_sales_order))
            if linked_sales_order :
                #CHECK IF ALL THE CRITERIAS ARE MATCHED IN ORDER TO BE LINKED TO QBO
                #1 TO CHECK IF QBO ID IS ATTACHED TO SO
                if linked_sales_order.quickbook_id:
                    _logger.info("QBO ID IS PRESENT TO SO")
                    #2.TO CHECK IF SO IS PRESENT IN QBO
                    linked_so = self.get_linked_sales_order_ref(linked_sales_order.quickbook_id)
                    if linked_so:
                        _logger.info("SALES ORDER IS PRESENT IN QBO")
                        #UPDATE LINKED TRANSACTION DETAILS
                        vals.update({
                                    "LinkedTxn": [{
                                        "TxnId": linked_sales_order.quickbook_id,
                                        "TxnType": "Estimate"
                                       }
                                    ]})
                    else:
                        _logger.info("SALES ORDER NOT PRESENT IN QBO")
                        raise ValidationError(_("Sales Order : %s  is not present in  Quickbooks." % (invoice.invoice_origin)))
                else : 
                    _logger.info("Linked Sales Order is not exported to Quickbooks")
                    raise ValidationError(_("Sales Order : %s linked to this Invoice is not exported to Quickbooks.Please export Sales Order first to link the invoice into Quickbooks " % (invoice.invoice_origin)))


        if invoice.partner_id.customer_rank:
            vals.update({'DocNumber': invoice.name,
                         'CustomerRef': {'value': self.env['res.partner'].get_qbo_partner_ref(invoice.partner_id)}})
        elif invoice.partner_id.supplier_rank:
#             if invoice.invoice_sequence_number_next_prefix and invoice.invoice_sequence_number_next :
#                 _logger.info("VENDOR BILL NUMBER IS ---> {} {}".format(invoice.invoice_sequence_number_next_prefix,invoice.invoice_sequence_number_next))
#                 vendor_bill_ref_num = "{}{}".format(invoice.invoice_sequence_number_next_prefix,invoice.invoice_sequence_number_next)
#                 vals.update({'DocNumber' : vendor_bill_ref_num})
            vals.update({'DocNumber': invoice.name,
                        'VendorRef': {'value': self.env['res.partner'].get_qbo_partner_ref(invoice.partner_id)}})

        arr = []
        tax_id = 0
        lst_line = []
        for line in invoice.invoice_line_ids:
            line_vals = self._prepare_invoice_export_line_dict(line)
            lst_line.append(line_vals)

            if line.tax_ids.id:
                if line.tax_ids.qbo_tax_id:
                    tax_id = line.tax_ids.id
                    arr.append(tax_id)
                elif not line.tax_ids.qbo_tax_id:
                    exported = self.env['account.tax'].export_one_tax_at_a_time(line.tax_ids)

                    is_exported = self.env['account.tax'].search([('id', '=', line.tax_ids.id)])
                    if is_exported:
                        if line.tax_ids.qbo_tax_id:
                            tax_id = line.tax_ids.id
                            arr.append(tax_id)
        if tax_id:
            # Set Tax type Like Inclusive or Exclusive or Out of scope Tax
            if invoice.tax_state:
                if invoice.tax_state == 'exclusive':
                    vals.update({"GlobalTaxCalculation": "TaxExcluded"})
                elif invoice.tax_state == 'inclusive':
                    vals.update({"GlobalTaxCalculation": "TaxInclusive"})
                elif invoice.tax_state == 'notapplicable':
                    vals.update({"GlobalTaxCalculation": "NotApplicable"})
        vals.update({'Line': lst_line})

        if tax_id:
            j = 0
            for i in arr:
                if len(arr) == 1:
                    tax_added = self.env['account.tax'].search([('id', '=', tax_id)])

                    vals.update({"TxnTaxDetail": {
                        "TxnTaxCodeRef": {
                            "value": tax_added.qbo_tax_id
                        }}})
                if j < len(arr) - 1:
                    if arr[j] == arr[j + 1]:
                        j = j + 1

                        tax_added = self.env['account.tax'].search([('id', '=', tax_id)])

                        vals.update({"TxnTaxDetail": {
                            "TxnTaxCodeRef": {
                                "value": tax_added.qbo_tax_id
                            }}})
                    else:
                        raise UserError("You need to add same tax for the required orderlines.")

        return vals

    @api.model
    def export_to_qbo(self):
        """export account invoice to QBO"""
        quickbook_config = self.env['res.users'].search([('id', '=', 2)]).company_id

        if self._context.get('active_ids'):
            invoices = self.browse(self._context.get('active_ids'))
        else:
            invoices = self

        if len(invoices) == 1:
            if invoices.move_type == 'entry':
                if invoices.qbo_invoice_id:
                    raise ValidationError(_("%s Journal Entry is already exported to QBO. Please, export a different Journal Entry." % invoices.name))

        for invoice in invoices:
            if invoice.move_type == 'entry':  # Journal Entry
                invoice.export_journal_entry()

            if invoice.move_type == 'out_refund' or invoice.move_type == 'in_refund':
                raise ValidationError(
                                _("Currently Export function for Credit notes /  Refunds and Payments are not available"))

            if self._context.get('active_ids'):
                if len(invoices) == 1:
                    if invoice.qbo_invoice_id:
                        if invoice.partner_id.customer_rank:
                            raise ValidationError(
                                _("Invoice is already exported to QBO. Please, export a different invoice."))
                        if invoice.partner_id.supplier_rank:
                            raise ValidationError(
                                _("Vendor Bill is already exported to QBO. Please, export a different Vendor Bill."))
            if len(invoices) > 1:
                if invoice.qbo_invoice_id:
                    if invoice.partner_id.customer_rank:
                        _logger.info("Invoice is already exported to QBO")
                    if invoice.partner_id.supplier_rank:
                        _logger.info("Vendor Bill is already exported to QBO")

            if not invoice.qbo_invoice_id:
                if invoice.state == 'posted':
                    vals = invoice._prepare_invoice_export_dict()
                    parsed_dict = json.dumps(vals)
                    _logger.info('\n\n\nExport Dict for Invoice/BILL : \n\n{}'.format(parsed_dict))
                    if quickbook_config.access_token:
                        access_token = quickbook_config.access_token
                    if quickbook_config.realm_id:
                        realmId = quickbook_config.realm_id

                    if access_token:
                        headers = {}
                        headers['Authorization'] = 'Bearer ' + str(access_token)
                        headers['Content-Type'] = 'application/json'

                        if not invoice.partner_id.customer_rank and not invoice.partner_id.supplier_rank:
                            raise UserError('Please define rank either customer/vendor')
                        # print(headers,"___________________1")
                        if invoice.partner_id.customer_rank:
                            result = requests.request('POST', quickbook_config.url + str(realmId) + "/invoice",
                                                      headers=headers, data=parsed_dict)
                        elif invoice.partner_id.supplier_rank:
                            result = requests.request('POST', quickbook_config.url + str(realmId) + "/bill",
                                                      headers=headers, data=parsed_dict)
                        # print("___________________1", result.text,parsed_dict)

                        if result.status_code == 200:
                            response = quickbook_config.convert_xmltodict(result.text)
                            # print("___________________1", response, parsed_dict)
                            # update QBO invoice id
                            if invoice.partner_id.customer_rank:
                                invoice.qbo_invoice_id = response.get('IntuitResponse').get('Invoice').get('Id')
                                invoice.qbo_invoice_name = response.get('IntuitResponse').get('Invoice').get('DocNumber')
                                self._cr.commit()
                            elif invoice.partner_id.supplier_rank:
                                invoice.qbo_invoice_id = response.get('IntuitResponse').get('Bill').get('Id')
                                invoice.qbo_invoice_name = response.get('IntuitResponse').get('Bill').get('DocNumber')
                                self._cr.commit()
                            _logger.info(_("%s exported successfully to QBO" % (invoice.name)))

                        else:
                            _logger.info(_("STATUS CODE : %s" % (result.status_code)))
                            _logger.info(_("RESPONSE DICT : %s" % (result.text)))
                            response = json.loads(result.text)
                            if response.get('Fault'):
                                if response.get('Fault').get('Error'):
                                    for message in response.get('Fault').get('Error'):
                                        if message.get('Detail') and message.get('Message'):
                                            raise UserError(message.get('Message') + "\n\n" + message.get('Detail'))
                            #
                            # _logger.error(_("[%s] %s" % (result.status_code, result.reason)))
                            # raise ValidationError(_("[%s] %s %s" % (result.status_code, result.reason, result.text)))
                else:
                    if len(invoices) == 1:
                        if invoice.move_type == 'in_invoice' :
                            raise ValidationError(_("Only posted state Vendor Bill is exported to QBO."))
                        if invoice.move_type == 'out_invoice' :
                            raise ValidationError(_("Only posted state Invoice is exported to QBO."))
                        if invoice.move_type == 'in_refund' :
                            raise ValidationError(_("Only posted state Customer Credit Note is exported to QBO."))
                        if invoice.move_type == 'out_refund' :
                            raise ValidationError(_("Only posted state Vendor Credit Note is exported to QBO."))

#                         if invoice.partner_id.customer_rank:
#                             raise ValidationError(_("Only posted state Invoice is exported to QBO."))
#                         if invoice.partner_id.supplier_rank:
#                             raise ValidationError(_("Only posted state Vendor bill is exported to QBO."))
                        
    @api.model
    def export_journal_entry(self):
        """export journal enrty to QBO"""
        quickbook_config = self.env['res.users'].search([('id', '=', 2)]).company_id

        if quickbook_config.access_token:
            access_token = quickbook_config.access_token
        if quickbook_config.realm_id:
            realmId = quickbook_config.realm_id

        if access_token:
            headers = {}
            headers['Authorization'] = 'Bearer ' + str(access_token)
            headers['Content-Type'] = 'application/json'


        invoice = self
        for t in invoice:
            if t.move_type == 'entry':  #  Journal Entry
                if not t.qbo_invoice_id:
                    # print('\n\nNot Exported Yet\n\n')
                    if t.state == 'posted':
                        # print('\n\nIs Posted\n\n')
                        values = t.prepare_qbo_journal_export_dict()
                        parsed_dict = json.dumps(values)

                        _logger.info("\n\nPrepared Dictionary :   {} ".format(parsed_dict))

                        data = requests.request('POST', quickbook_config.url + str(realmId) + "/journalentry",
                                                  headers=headers, data=parsed_dict)
                        # print('\n\n++++++++++++++++++++++ Response : ', data)
                        if data.status_code == 200:
                            response_data = quickbook_config.convert_xmltodict(data.text)
                            # update QBO invoice id
                            # print('\n\nResponse : ', response_data)
                            if response_data.get('IntuitResponse').get('JournalEntry'):
                                t.qbo_invoice_id = response_data.get('IntuitResponse').get('JournalEntry').get('Id')
                                self._cr.commit()
                                _logger.info(_("Exported successfully to QBO"))


                        else:
                            _logger.info(_("STATUS CODE : %s" % (data.status_code)))
                            _logger.info(_("RESPONSE DICT : %s" % (data.text)))
                            response = json.loads(data.text)
                            if response.get('Fault'):
                                if response.get('Fault').get('Error'):
                                    for message in response.get('Fault').get('Error'):
                                        if message.get('Detail') and message.get('Message'):
                                            raise UserError(message.get('Message') + "\n\n" + message.get('Detail'))

                            _logger.info(_("[%s] %s" % (data.status_code, data.reason)))

                            raise ValidationError(_("[%s] %s %s" % (data.status_code, data.reason, data.text)))


                    else:
                        raise ValidationError(_("Only Posted state Invoice is exported to QBO."))
                else:
                    _logger.info(_("%s Journal Entry is already exported to QBO. Please, export a different Journal Entry." % t.name))


        success_form = self.env.ref('pragmatic_quickbooks_connector.export_successfull_view', False)
        return {
            'name': _('Notification'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'res.company.message',
            'views': [(success_form.id, 'form')],
            'view_id': success_form.id,
            'target': 'new',
        }

    def prepare_qbo_journal_export_dict(self):
        company = self.env['res.users'].search([('id', '=', 2)]).company_id
        vals = {}
        narration=None
        if self.ref:
            narration = self.ref

        if self.date:
            date = str(self.date)

        #  Preparing Lines for export Journal
        journal_line_ids = []
        line_amount = None
        currency_name =''
        if self.line_ids:
            for line in self.line_ids:
                line_dict = {}
                postingtype=''

                if line.credit > 0:
                    postingtype = 'Credit'
                    line_amount = float(line.credit)
                elif line.debit > 0:
                    postingtype = 'Debit'
                    line_amount = float(line.debit)

                if line.currency_id and line.currency_id.name != company.currency_id.name and line.amount_currency:
                    currency_name=str(line.currency_id.name)
                    if line.amount_currency > 0:
                        postingtype = 'Credit'
                        line_amount = float(line.amount_currency)
                    elif line.amount_currency < 0:
                        postingtype = 'Debit'
                        line_amount = -1*float(line.amount_currency)
                if line.amount_currency:
                    if line.amount_currency > 0:
                        postingtype = 'Credit'
                        line_amount = float(line.amount_currency)
                    elif line.amount_currency < 0:
                        postingtype = 'Debit'
                        line_amount = -1*float(line.amount_currency)

                if line.account_id:
                    _logger.info('\n\n Acount ID : %s'%(line.account_id))
                    if line.account_id.qbo_id:
                        account_code = line.account_id.qbo_id
                        account_name = str(line.account_id.name)
                    else:
                        accounts = self.env['account.account'].browse(line.account_id.id)
                        # self.export_to_qbo_main(accounts)
                        accounts.export_single_account()
                        raise UserError(
                            'Account Code ' + line.account_id.code + ' doesnot exists for QBO in Odoo. ')

                if not postingtype:
                    raise UserError(
                        'Joual Entry ' + self.name + ' doesnot have Credit Debits. ')

                line_dict.update({
                    "JournalEntryLineDetail": {
                        "PostingType": postingtype,
                        "AccountRef": {
                            "name": account_name,
                            "value": account_code
                        }
                    },
                    'DetailType': 'JournalEntryLineDetail',
                    'Amount': line_amount,
                    'Description': line.name,

                })

                # print('line_idct : \n\n', line_dict)
                journal_line_ids.append(line_dict)
        vals.update({"Line": journal_line_ids})
        vals.update({
            "TxnDate": date,
            "PrivateNote": narration,
            "CurrencyRef": {"value": 'USD', "name": 'United States Dollar'}
        })
        if currency_name:
            vals.update({
                "CurrencyRef": {"value": currency_name, "name": currency_name}
            })

        # print('\n\n\n Prepeared Dictionary : ', vals, '\n\n\n\n')
        return vals