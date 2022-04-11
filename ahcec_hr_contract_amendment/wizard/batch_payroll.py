# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class BatchPayroll(models.TransientModel):
    _name = 'batch.payroll'

    date_from = fields.Date(
        'Date From',
        required = True,
    )
    date_to = fields.Date(
        'Date To',
        required = True,
    )
    is_aramco_smdcad = fields.Boolean('Include Aramco SMPCAD')

    def generate_payslips(self):
        batch_id = self.env['hr.payslip.run'].create({
            'name': 'Payslip Batch For ' + str(self.date_from)+ ' -- ' + str(self.date_to),
            'date_start': self.date_from,
            'date_end': self.date_to
        })

        generate_payslip = self.env['hr.payslip.employees']
        if not self.is_aramco_smdcad:
            contract_ids = self.env['hr.contract'].search(
                [('state', 'in', ['open', 'pending']), ('is_aramco_smdcad', '=', False)])
        else:
            contract_ids = self.env['hr.contract'].search([('state', 'in', ['open', 'pending'])])
        lst = []
        employee_ids = []
        for line in contract_ids:
            employee_ids.append(line.employee_id)
            lst.append({
                'name': line.employee_id.id,
                'work_phone': line.employee_id.work_phone or None,
                'work_email': line.employee_id.work_email or None,
                'department_id': line.employee_id.department_id or None,
                'job_id': line.employee_id.job_id or None,
                'parent_id': line.employee_id.parent_id or None,
            })
        generate_payslip.create({
            'employee_ids': lst
        })

        payslips = self.env['hr.payslip']
        [run_data] = batch_id.read(
            ['date_start', 'date_end', 'credit_note'])
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not employee_ids:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        for employee in employee_ids:
            slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id,
                                                                    contract_id=False)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': batch_id.id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [
                    (0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'company_id': employee.company_id.id,
            }
            print(res['name'])
            payslips += self.env['hr.payslip'].create(res)
        print(len(payslips))
        payslips.compute_sheet_ahcec()
        return {'type': 'ir.actions.act_window_close'}

        
