# __author__ = 'thanhchatvn'


from osv import osv
import logging
import jasper_reports

class sale_order_report(osv.osv_memory):

    _name='sale.order.report'

    __logger = logging.getLogger(_name)


    def start_report(self, cr, uid, ids, data, context=None):
        """
        cr: self cusor
        uid: self uid
        ids self wizard ids
        data: self data
        example:
        ==================================
         {'lang': u'en_US', 'tz': False, 'uid': 1, 'form': {}, 'ids': [1, 2, 3, 4, 5, 6, 7, 8], 'model': 'sale.order'}
        ==================================
        """
        self.__logger.info('begin start_report()')
        for wiz_obj in self.read(cr,uid,ids):
            if 'form' not in data or not data:
                data['form'] = {}

            # Model auto filter data record
            data['model'] = 'sale.order'


            # Args Ids Jasper Server Filter
            # If You Change data filter, You can create new function and this function return new list ids
            # Good Luck.

            data['ids']=self.pool.get(data['model']).search(cr,uid,[])

            # end filter, return report name and data filter
            # ^_^
            # Have Fund for You.
            # thanhchatvn@gmail.com


            self.__logger.info('data: %s' % data)
            self.__logger.info('end start_report()')
            return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'jasper_report_sale_order_example',
                    'datas': data,
            }
sale_order_report()


jasper_reports.report_jasper(
    'report.jasper_report_sale_order_example',
    'sale_order'
)


