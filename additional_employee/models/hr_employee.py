from odoo import fields, api, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    city = fields.Char(string='City')
    # المهنة حسب الإقامة السعودي حسب التامينات
    work_iqama = fields.Char(string='Work Iqama', help="المهنة حسب الإقامة السعودي حسب التامينات")

