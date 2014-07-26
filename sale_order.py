from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from openerp import pooler
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp import netsvc
import logging
_logger=logging.getLogger(__name__)

class sale_order(osv.osv):
    _inherit='sale.order'
    
    # Compute all of the line subtotal and sum all subtotal
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):                
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            tax_obj = self.pool.get('account.tax')
            cur_obj = self.pool.get('res.currency')
            if order.disc_type == 'unit_price':
                for line in order.order_line:                        
                    if line.discount and line.discount_amount:
                        price = ((line.price_unit * (1 - (line.discount or 0.0)  / 100.0)) - line.discount_amount)
                        taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                        cur = line.order_id.pricelist_id.currency_id
                        #res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                        val1+=cur_obj.round(cr, uid, cur, taxes['total'])                    
                    if not line.discount and not line.discount_amount:
                        price = line.price_unit
                        taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                        cur = line.order_id.pricelist_id.currency_id
                        #res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                        val1+=cur_obj.round(cr, uid, cur, taxes['total'])
                    if line.discount and not line.discount_amount:                
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                        cur = line.order_id.pricelist_id.currency_id
                        #res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                        val1+=cur_obj.round(cr, uid, cur, taxes['total'])
                    if line.discount_amount and not line.discount:
                        price = line.price_unit - (line.discount_amount or 0.0)
                        taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                        cur = line.order_id.pricelist_id.currency_id
                        #res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                        val1+=cur_obj.round(cr, uid, cur, taxes['total'])
                    
                        #val1 += line.price_subtotal
                        val += self._amount_line_tax(cr, uid, line, context=context)
            elif order.disc_type == 'qty':                
                for line in order.order_line:                        
                    if line.discount and line.discount_amount:
                        price = line.price_unit
                        taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                        cur = line.order_id.pricelist_id.currency_id
                        #res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                        val1+=((cur_obj.round(cr, uid, cur, taxes['total']) * (1 - (line.discount or 0.0)  / 100.0)) - line.discount_amount)
                    if not line.discount and not line.discount_amount:
                        price = line.price_unit
                        taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                        cur = line.order_id.pricelist_id.currency_id
                        #res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                        val1+=cur_obj.round(cr, uid, cur, taxes['total'])
                    if line.discount and not line.discount_amount:                
                        price = line.price_unit
                        taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                        cur = line.order_id.pricelist_id.currency_id
                        #res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                        val1+=cur_obj.round(cr, uid, cur, taxes['total']) * (1 - (line.discount or 0.0) / 100.0)
                    if line.discount_amount and not line.discount:
                        price = line.price_unit 
                        taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                        cur = line.order_id.pricelist_id.currency_id
                        #res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                        val1+=cur_obj.round(cr, uid, cur, taxes['total'])- (line.discount_amount or 0.0)
                    
                        #val1 += line.price_subtotal
                        val += self._amount_line_tax(cr, uid, line, context=context)
                
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res
        
    def _get_order(self, cr, uid, ids, context=None):        
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()
        
    _columns={
        'disc_type':fields.selection([('unit_price','Based on Unit Price'),('qty','Based on Total Qty')],'Discount Type',required=True,help="Base on Unit Price --> calculation depends on unit price; Based on Total Qty --> Calculation depends on total qty multiply unit price"),
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The total amount."),
    }
    
    def action_invoice_create(self, cr, uid, ids, grouped=False, states=None, date_invoice = False, context=None):    
        if states is None:
            states = ['confirmed', 'done', 'exception']
        res = False
        invoices = {}
        invoice_ids = []
        invoice = self.pool.get('account.invoice')
        obj_sale_order_line = self.pool.get('sale.order.line')
        partner_currency = {}
        if context is None:
            context = {}
        # If date was specified, use it as date invoiced, usefull when invoices are generated this month and put the
        # last day of the last month as invoice date
        if date_invoice:
            context['date_invoice'] = date_invoice
        for o in self.browse(cr, uid, ids, context=context):
            currency_id = o.pricelist_id.currency_id.id
            if (o.partner_id.id in partner_currency) and (partner_currency[o.partner_id.id] <> currency_id):
                raise osv.except_osv(
                    _('Error!'),
                    _('You cannot group sales having different currencies for the same partner.'))

            partner_currency[o.partner_id.id] = currency_id
            lines = []
            for line in o.order_line:
                if line.invoiced:
                    continue
                elif (line.state in states):
                    lines.append(line.id)
            created_lines = obj_sale_order_line.invoice_line_create(cr, uid, lines)
            if created_lines:
                invoices.setdefault(o.partner_id.id, []).append((o, created_lines))
        if not invoices:
            for o in self.browse(cr, uid, ids, context=context):
                for i in o.invoice_ids:
                    if i.state == 'draft':
                        return i.id
        for val in invoices.values():
            if grouped:
                res = self._make_invoice(cr, uid, val[0][0], reduce(lambda x, y: x + y, [l for o, l in val], []), context=context)
                invoice_ref = ''
                for o, l in val:
                    invoice_ref += o.name + '|'
                    self.write(cr, uid, [o.id], {'state': 'progress'})
                    cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%s,%s)', (o.id, res))
                invoice.write(cr, uid, [res], {'origin': invoice_ref, 'name': invoice_ref})
            else:
                for order, il in val:
                    res = self._make_invoice(cr, uid, order, il, context=context)
                    invoice_ids.append(res)
                    self.write(cr, uid, [order.id], {'state': 'progress'})
                    cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%s,%s)', (order.id, res))
        return res
    def action_invoice_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'invoice_except'}, context=context)
        return True

    def action_invoice_end(self, cr, uid, ids, context=None):
        for this in self.browse(cr, uid, ids, context=context):
            for line in this.order_line:
                if line.state == 'exception':
                    line.write({'state': 'confirmed'})
            if this.state == 'invoice_except':
                this.write({'state': 'progress'})
        return True
    
    def action_view_invoice(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing invoices of given sales order ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'account', 'action_invoice_tree1')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        #compute the number of invoices to display
        inv_ids = []
        for so in self.browse(cr, uid, ids, context=context):
            inv_ids += [invoice.id for invoice in so.invoice_ids]
        #choose the view_mode accordingly
        if len(inv_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, inv_ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = inv_ids and inv_ids[0] or False
        return result
        
    def _make_invoice(self, cr, uid, order, lines, context=None):        
        inv_obj = self.pool.get('account.invoice')
        obj_invoice_line = self.pool.get('account.invoice.line')
        if context is None:
            context = {}
        invoiced_sale_line_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', order.id), ('invoiced', '=', True)], context=context)
        from_line_invoice_ids = []
        for invoiced_sale_line_id in self.pool.get('sale.order.line').browse(cr, uid, invoiced_sale_line_ids, context=context):
            for invoice_line_id in invoiced_sale_line_id.invoice_lines:
                if invoice_line_id.invoice_id.id not in from_line_invoice_ids:
                    from_line_invoice_ids.append(invoice_line_id.invoice_id.id)
        for preinv in order.invoice_ids:
            if preinv.state not in ('cancel',) and preinv.id not in from_line_invoice_ids:
                for preline in preinv.invoice_line:
                    inv_line_id = obj_invoice_line.copy(cr, uid, preline.id, {'invoice_id': False, 'price_unit': -preline.price_unit})
                    lines.append(inv_line_id)
        inv = self._prepare_invoice(cr, uid, order, lines, context=context)
        #add sale type and pass to invoice
        inv.update({'sale_type':order.sale_type,'disc_type':order.disc_type})
        inv_id = inv_obj.create(cr, uid, inv, context=context)
        data = inv_obj.onchange_payment_term_date_invoice(cr, uid, [inv_id], inv['payment_term'], time.strftime(DEFAULT_SERVER_DATE_FORMAT))
        if data.get('value', False):
            inv_obj.write(cr, uid, [inv_id], data['value'], context=context)
        inv_obj.button_compute(cr, uid, [inv_id])
        return inv_id
        
sale_order()

class sale_order_line(osv.osv):
    _inherit="sale.order.line"
    
    # Compute all of the line subtotal
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):       
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        so_id = self.browse(cr,uid,ids,context)[0].order_id.id
        disc_type = self.pool.get('sale.order').browse(cr,uid,so_id,context).disc_type
        
        if disc_type == 'unit_price':  
            for line in self.browse(cr, uid, ids, context=context):
                if line.discount and line.discount_amount:                
                    price = ((line.price_unit * (1 - (line.discount or 0.0)  / 100.0)) - line.discount_amount)
                    taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                if not line.discount and not line.discount_amount:
                    price = line.price_unit
                    taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                if line.discount and not line.discount_amount:                
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                if line.discount_amount and not line.discount:
                    price = line.price_unit - (line.discount_amount or 0.0)
                    taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        elif disc_type == 'qty':
            for line in self.browse(cr, uid, ids, context=context):
                if line.discount and line.discount_amount:                
                    price = line.price_unit
                    taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id] = ((cur_obj.round(cr, uid, cur, taxes['total']) * (1 - (line.discount or 0.0)  / 100.0)) - line.discount_amount)
                if not line.discount and not line.discount_amount:
                    price = line.price_unit
                    taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
                if line.discount and not line.discount_amount:                
                    price = line.price_unit 
                    taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id] = cur_obj.round(cr, uid, cur, taxes['total']) * (1 - (line.discount or 0.0) / 100.0)
                if line.discount_amount and not line.discount:
                    price = line.price_unit 
                    taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])- (line.discount_amount or 0.0)
        return res
        
    
    _columns={
        'discount_amount': fields.float('Discount Amount', digits_compute= dp.get_precision('Discount Amount'), readonly=True, states={'draft': [('readonly', False)]}),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Sale Price'))
    }
    
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        """Prepare the dict of values to create the new invoice line for a
           sales order line. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: sale.order.line record to invoice
           :param int account_id: optional ID of a G/L account to force
               (this is used for returning products including service)
           :return: dict of values to create() the invoice line
        """
        res = {}
        if not line.invoiced:
            if not account_id:
                if line.product_id:
                    account_id = line.product_id.property_account_income.id
                    if not account_id:
                        account_id = line.product_id.categ_id.property_account_income_categ.id
                    if not account_id:
                        raise osv.except_osv(_('Error!'),
                                _('Please define income account for this product: "%s" (id:%d).') % \
                                    (line.product_id.name, line.product_id.id,))
                else:
                    prop = self.pool.get('ir.property').get(cr, uid,
                            'property_account_income_categ', 'product.category',
                            context=context)
                    account_id = prop and prop.id or False
            uosqty = self._get_line_qty(cr, uid, line, context=context)
            uos_id = self._get_line_uom(cr, uid, line, context=context)
            pu = 0.0
            if uosqty:
                pu = round(line.price_unit * line.product_uom_qty / uosqty,
                        self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
            fpos = line.order_id.fiscal_position or False
            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
            if not account_id:
                raise osv.except_osv(_('Error!'),
                            _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
            res = {
                'name': line.name,
                'sequence': line.sequence,
                'origin': line.order_id.name,
                'account_id': account_id,
                'price_unit': pu,
                'quantity': uosqty,
                'discount': line.discount,
                'discount_amount':line.discount_amount,
                'price_subtotal':line.price_subtotal,
                'uos_id': uos_id,
                'product_id': line.product_id.id or False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
                'account_analytic_id': line.order_id.project_id and line.order_id.project_id.id or False,
            }

        return res

    def invoice_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        create_ids = []
        sales = set()
        for line in self.browse(cr, uid, ids, context=context):
            vals = self._prepare_order_line_invoice_line(cr, uid, line, False, context)
            if vals:
                inv_id = self.pool.get('account.invoice.line').create(cr, uid, vals, context=context)
                cr.execute('insert into sale_order_line_invoice_rel (order_line_id,invoice_id) values (%s,%s)', (line.id, inv_id))
                sales.add(line.order_id.id)
                create_ids.append(inv_id)
        # Trigger workflow events
        wf_service = netsvc.LocalService("workflow")
        for sale_id in sales:
            wf_service.trg_write(uid, 'sale.order', sale_id, cr)
        return create_ids
sale_order_line()
