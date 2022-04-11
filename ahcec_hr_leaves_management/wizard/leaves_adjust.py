
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from datetime import datetime
from datetime import date
import time
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


class leaves_adjustment(models.TransientModel):
    _name = 'leaves.adjustment'
    _description = "Leaves Adjust"

    count = fields.Integer('Adjustment Count',readonly=True)

    def adjustment_leave(self):
        leaves = self.env['hr.holidays'].search([('state','not in',('cancel', 'refuse')),('type','=','remove')])
        ct = 0
        for leave in leaves:
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
                    print('Date From',leave.date_from,'== Date To:',leave.date_to)
                    ct += 1
                    self.update({'count':ct})
                except Exception as e:
                    print(e)
        return {'type': 'ir.actions.act_window_close'}