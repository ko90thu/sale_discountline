import logging

from openerp.osv import fields, osv
from openerp import pooler
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class sale_discount_configuration(osv.osv_memory):	
	_inherit = 'sale.config.settings'
	_columns={	
		'group_sale_multi_discount': fields.boolean("Allow Discount Types for Sale Order Lines",
            implied_group='sale_discountline.group_sale_multi_discount',
            help="This includes all the discount features concerned with sale."),
	}
sale_discount_configuration()
