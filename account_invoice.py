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


class account_invoice(osv.osv):
	_inherit='account.invoice'
	
	def _amount_all(self, cr, uid, ids, name, args, context=None):
		res = {}
		for invoice in self.browse(cr, uid, ids, context=context):
			res[invoice.id] = {
				'amount_untaxed': 0.0,
				'amount_tax': 0.0,
				'amount_total': 0.0
			}
			for line in invoice.invoice_line:
				res[invoice.id]['amount_untaxed'] += line.price_subtotal
			for line in invoice.tax_line:
				res[invoice.id]['amount_tax'] += line.amount
			res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed']
		return res
		#import pdb;
		#pdb.set_trace()		
		#tax_obj = self.pool.get('account.tax')
		#cur_obj = self.pool.get('res.currency')
		#res = {}
		#for invoice in self.browse(cr, uid, ids, context=context):
			#res[invoice.id] = {
				#'amount_untaxed': 0.0,
				#'amount_tax': 0.0,
				#'amount_total': 0.0
			#}
			#if invoice.disc_type == 'unit_price':
				#for line in invoice.invoice_line:
					#_logger.info('Line is %r',line)
					#if line.discount and line.discount_amount:
						#price = (line.price_unit * (1-(line.discount or 0.0)/100.0)-line.discount_amount)
						#if line.invoice_id:
							#cur = line.invoice_id.currency_id
							#res[invoice.id]['amount_untaxed'] +=  cur_obj.round(cr, uid, cur, price)
					#if not line.discount and not line.discount_amount:
						#price = line.price_unit
						#if line.invoice_id:
							#cur = line.invoice_id.currency_id
							#res[invoice.id]['amount_untaxed'] +=  cur_obj.round(cr, uid, cur, price)
					#if not line.discount and line.discount_amount:
						#price = line.price_unit -line.discount_amount
						#if line.invoice_id:
							#cur = line.invoice_id.currency_id
							#res[invoice.id]['amount_untaxed'] +=  cur_obj.round(cr, uid, cur, price)
					#if line.discount and not line.discount_amount:
						#price = line.price_unit * (1-(line.discount or 0.0)/100.0)
						#if line.invoice_id:
							#cur = line.invoice_id.currency_id
							#res[invoice.id]['amount_untaxed'] +=  cur_obj.round(cr, uid, cur, price)
			#elif invoice.disc_type == 'qty':
				#for line in invoice.invoice_line:
					#_logger.info('Line is %r',line)
					#if line.discount and line.discount_amount:
						#price = line.price_unit 
						#if line.invoice_id:
							#cur = line.invoice_id.currency_id
							#res[invoice.id]['amount_untaxed'] +=  (cur_obj.round(cr, uid, cur, price)* (1-(line.discount or 0.0)/100.0)-line.discount_amount)
					#if not line.discount and not line.discount_amount:
						#price = line.price_unit
						#if line.invoice_id:
							#cur = line.invoice_id.currency_id
							#res[invoice.id]['amount_untaxed'] +=  cur_obj.round(cr, uid, cur, price)
					#if not line.discount and line.discount_amount:
						#price = line.price_unit
						#if line.invoice_id:
							#cur = line.invoice_id.currency_id
							#res[invoice.id]['amount_untaxed'] +=  cur_obj.round(cr, uid, cur, price)-line.discount_amount
					#if line.discount and not line.discount_amount:
						#price = line.price_unit 
						#if line.invoice_id:
							#cur = line.invoice_id.currency_id
							#res[invoice.id]['amount_untaxed'] +=  cur_obj.round(cr, uid, cur, price)* (1-(line.discount or 0.0)/100.0)
			#for line in invoice.tax_line:
				#res[invoice.id]['amount_tax'] += line.amount
			#res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed']
		#return res
	
	def _get_invoice_line(self, cr, uid, ids, context=None):
		result = {}
		for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
			result[line.invoice_id.id] = True
		return result.keys()

	def _get_invoice_tax(self, cr, uid, ids, context=None):
		result = {}
		for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
			result[tax.invoice_id.id] = True
		return result.keys()
        
	_columns={
		'disc_type':fields.selection([('unit_price','Based on Unit Price'),('qty','Based on Total Qty')],'Discount Type',required=True,help="Base on Unit Price --> calculation depends on unit price; Based on Total Qty --> Calculation depends on total qty multiply unit price"),
		 'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Subtotal', track_visibility='always',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Tax',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
	}
	
	def _find_partner(self, inv):
		'''
		Find the partner for which the accounting entries will be created
		'''
		#if the chosen partner is not a company and has a parent company, use the parent for the journal entries 
		#because you want to invoice 'Agrolait, accounting department' but the journal items are for 'Agrolait'
		part = inv.partner_id
		if part.parent_id and not part.is_company:
			part = part.parent_id
		return part

account_invoice()

class account_invoice_line(osv.osv):
	_inherit='account.invoice.line'
	
	
	def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
		res = {}
		tax_obj = self.pool.get('account.tax')
		cur_obj = self.pool.get('res.currency')		
		
		
		for line in self.browse(cr, uid, ids):
			if line.invoice_id.disc_type == 'unit_price':
				if line.discount and line.discount_amount:
					price = (line.price_unit * (1-(line.discount or 0.0)/100.0)-line.discount_amount)
					taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
					res[line.id] = taxes['total']
					if line.invoice_id:
						cur = line.invoice_id.currency_id
						res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
				if not line.discount and not line.discount_amount:
					price = line.price_unit
					taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
					res[line.id] = taxes['total']
					if line.invoice_id:
						cur = line.invoice_id.currency_id
						res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
				if not line.discount and line.discount_amount:
					price = line.price_unit - line.discount_amount
					taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
					res[line.id] = taxes['total']
					if line.invoice_id:
						cur = line.invoice_id.currency_id
						res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
				if not line.discount_amount and line.discount:
					price = line.price_unit * (1-(line.discount or 0.0)/100.0)
					taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
					res[line.id] = taxes['total']
					if line.invoice_id:
						cur = line.invoice_id.currency_id
						res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
					
			elif line.invoice_id.disc_type == 'qty':
				if line.discount and line.discount_amount:
					price = line.price_unit 
					taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
					res[line.id] =(taxes['total'] * (1-(line.discount or 0.0)/100.0)-line.discount_amount)
					if line.invoice_id:
						cur = line.invoice_id.currency_id
						res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
				if not line.discount and not line.discount_amount:
					price = line.price_unit
					taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
					res[line.id] = taxes['total']
					if line.invoice_id:
						cur = line.invoice_id.currency_id
						res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
				if not line.discount and line.discount_amount:
					price = line.price_unit 
					taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
					res[line.id] = taxes['total']- line.discount_amount
					if line.invoice_id:
						cur = line.invoice_id.currency_id
						res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])					
				if not line.discount_amount and line.discount:
					price = line.price_unit 
					taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
					res[line.id] = taxes['total']* (1-(line.discount or 0.0)/100.0)
					if line.invoice_id:
						cur = line.invoice_id.currency_id
						res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
		return res
        
	_columns={
		'discount_amount': fields.float('Discount Amount', digits_compute= dp.get_precision('Discount Amount')),
		'price_subtotal': fields.function(_amount_line, string='Amount', type="float",digits_compute= dp.get_precision('Account'), store=True),
	}

account_invoice_line()
