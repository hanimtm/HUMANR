# -*- coding - utf:8 -*-

from datetime import datetime
from datetime import date
import time
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


class leaves_adjustment(models.TransientModel):
    _inherit = 'leaves.adjustment'

    day_from = fields.Date('From Date', required=True)
    day_end = fields.Date('End Date', required=True)
    # def adjustment_leave_new(self):
    #     leaves = self.env['hr.holidays'].search([('state','not in',('cancel', 'refuse')),('type','=','remove')])
    #     ct = 0
    #     for leave in leaves:
    #         print(leave.employee_id.employee_code)
    #         if leave.date_from and leave.date_to and leave.date_from < leave.date_to:
    #             try:
    #                 dt = datetime.combine(date.today(), datetime.min.time())
    #                 print('Date From 1;', leave.date_from, '== Date To:', leave.date_to)
    #                 date_to = datetime.strptime(leave.date_to,'%Y-%m-%d %H:%M:%S').date()
    #                 date_from = datetime.strptime(leave.date_from, '%Y-%m-%d %H:%M:%S').date()
    #
    #                 # leave.date_to = datetime.strptime(str(date_to) +" 17:00:00","%Y-%m-%d %H:%M:%S")
    #                 # leave.date_from = datetime.strptime(str(date_from)+" 07:00:00","%Y-%m-%d %H:%M:%S")
    #
    #
    #                 leave.date_to = datetime.combine(date_to, datetime.strptime('14:00:00','%H:%M:%S').time())
    #                 leave.date_from = datetime.combine(date_from, datetime.strptime('04:00:00','%H:%M:%S').time())
    #
    #                 leave.number_of_days_temp = leave._get_number_of_days(leave.date_from, leave.date_to, leave.employee_id.id)
    #                 leave.calculate_leave_details()
    #                 print('!! Date From',leave.date_from,'== Date To:',leave.date_to)
    #                 ct += 1
    #                 self.update({'count':ct})
    #             except Exception as e:
    #                 print(e)
    #     return {'type': 'ir.actions.act_window_close'}

    def adjustment_leave_new(self):

        date1 = datetime.strptime(self.day_from, '%Y-%m-%d')
        day_from_start = fields.Datetime.to_string(
            datetime(year=date1.year, month=date1.month, day=date1.day, hour=00, minute=00, second=00))

        date2 = datetime.strptime(self.day_end, '%Y-%m-%d')
        day_from_end = fields.Datetime.to_string(
            datetime(year=date2.year, month=date2.month, day=date2.day, hour=23, minute=59, second=59))
        holiday_ids = self.env['hr.holidays'].sudo().search([('type', '=', 'remove'),
                                                             ('state','not in',('cancel', 'refuse')),
                                                             '|',
                                                             '&',
                                                             ('date_from', '>=', str(day_from_start)),
                                                             ('date_from', '<=', str(day_from_end)),
                                                             '&',
                                                             ('date_to', '>=', str(day_from_start)),
                                                             ('date_to', '<=', str(day_from_end))
                                                             ])


        # leaves = self.env['hr.holidays'].search([('state','not in',('cancel', 'refuse')),('type','=','remove')])
        ct = 0
        for leave in holiday_ids:
            print(leave.employee_id.employee_code)
            if leave.date_from and leave.date_to and leave.date_from < leave.date_to:
                try:
                    dt = datetime.combine(date.today(), datetime.min.time())
                    print('Date From 1;', leave.date_from, '== Date To:', leave.date_to)
                    date_to = datetime.strptime(leave.date_to,'%Y-%m-%d %H:%M:%S').date()
                    date_from = datetime.strptime(leave.date_from, '%Y-%m-%d %H:%M:%S').date()

                    # leave.date_to = datetime.strptime(str(date_to) +" 17:00:00","%Y-%m-%d %H:%M:%S")
                    # leave.date_from = datetime.strptime(str(date_from)+" 07:00:00","%Y-%m-%d %H:%M:%S")


                    leave.date_to = datetime.combine(date_to, datetime.strptime('14:00:00','%H:%M:%S').time())
                    leave.date_from = datetime.combine(date_from, datetime.strptime('04:00:00','%H:%M:%S').time())

                    leave.number_of_days_temp = leave._get_number_of_days(leave.date_from, leave.date_to, leave.employee_id.id)
                    leave.calculate_leave_details()
                    print('!! Date From',leave.date_from,'== Date To:',leave.date_to)
                    ct += 1
                    self.update({'count':ct})
                except Exception as e:
                    print(e)
        return {'type': 'ir.actions.act_window_close'}

#
# class hr_leaves_adjustment(models.Model):
#     _inherit = 'hr.holidays'
# #
#     def adjustment_leave_new(self):
#         leaves = self.env['hr.holidays'].search([('state','not in',('cancel', 'refuse')),('type','=','remove')])
#         ct = 0
#         for leave in leaves:
#             if leave.date_from and leave.date_to and leave.date_from < leave.date_to:
#                 try:
#                     dt = datetime.combine(date.today(), datetime.min.time())
#                     # print('Date From 1;', leave.date_from, '== Date To:', leave.date_to)
#                     date_to = datetime.strptime(leave.date_to,'%Y-%m-%d %H:%M:%S').date()
#                     date_from = datetime.strptime(leave.date_from, '%Y-%m-%d %H:%M:%S').date()
#
#                     # leave.date_to = datetime.strptime(str(date_to) +" 17:00:00","%Y-%m-%d %H:%M:%S")
#                     # leave.date_from = datetime.strptime(str(date_from)+" 07:00:00","%Y-%m-%d %H:%M:%S")
#
#
#                     leave.date_to = datetime.combine(date_to, datetime.strptime('14:00:00','%H:%M:%S').time())
#                     leave.date_from = datetime.combine(date_from, datetime.strptime('04:00:00','%H:%M:%S').time())
#
#                     leave.number_of_days_temp = leave._get_number_of_days(leave.date_from, leave.date_to, leave.employee_id.id)
#                     leave.calculate_leave_details()
#                     # print('!! Date From',leave.date_from,'== Date To:',leave.date_to)
#                     ct += 1
#                     self.update({'count':ct})
#                 except Exception as e:
#                     print(e)
#         return {'type': 'ir.actions.act_window_close'}