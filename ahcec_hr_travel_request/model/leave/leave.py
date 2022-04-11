from odoo import api,fields,models,_
from datetime import date, datetime
from odoo.exceptions import UserError


# class HolidaysType(models.Model):
#     _inherit = "hr.holidays.status"
#
#     ticket_request = fields.Boolean('Allow Ticket Request')

class HrLeave(models.Model):
    _inherit = 'hr.holidays'

    need_ticket = fields.Boolean('Need Ticket')
    ticket_request = fields.Boolean(related='holiday_status_id.ticket_request')
    ticket_id = fields.Many2one('hr.travel.request','Ticket Request')
    travellers = fields.Selection(
        selection=[('employee', 'Employee Only'), ('employee_dependent', 'Employee & Dependants'),
                   ('dependent', 'Dependants Only')],
        states={'draft': [('readonly', False)]},
        string='Travellers'
    )

    dependents = fields.Many2many('employee.dependent', 'ticket_leave_dependent_rel', string='Dependents',
                                  states={'draft': [('readonly', False)]})
    request_type = fields.Selection(
        selection=[('ticket', 'Ticket Only'), ('ticket_reentry', 'Ticket & Re-Entry'),
                   ('reentry', 'Re-Entry Only')],
        states={'draft': [('readonly', False)]},
        string='Request Type'
    )

    def create_ticket_request(self):
        view_id = self.env['ir.model.data'].get_object_reference(
            'ahcec_hr_travel_request',
            'view_hr_travel_request_form')[1]
        return {
            'name': _('Payments'),
            'view_mode': 'form',
            'res_model': 'hr.travel.request',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_name': self.name or '' + ' / ' + self.holiday_status_id.name,
                'default_employee_id': self.employee_id.id,
                'default_start_date': datetime.strptime(self.date_from, "%Y-%m-%d %H:%M:%S").date(),
                'default_end_date': datetime.strptime(self.date_to, "%Y-%m-%d %H:%M:%S").date(),
                'default_dependents': self.dependents.ids,
                'default_request_type': self.request_type,
                'default_travellers': self.travellers,
            }
        }

    def action_validate(self):
        res = super(HrLeave, self).action_validate()

        # def done_purchase_fun(self):
        #     for rec in self:
        #         line_ids = []
        #         move = {
        #             'name': '/',
        #             'journal_id': rec.company_id.accrual_journal.id,
        #             'date': fields.Date.today(),
        #         }
        #         credit = 0
        #         if not rec.company_id.accrual_account or not rec.company_id.accrual_journal:
        #             raise UserError(
        #                 _("Please assign the default Accrual values"))
        #         else:
        #             for line in rec.order_line:
        #                 debit_account = self.env['ir.config_parameter'].sudo().get_param('default_leave_salary')
        #                 credit_account = self.env['ir.config_parameter'].sudo().get_param('default_leave_salary')
        #                 if not :
        #                     raise UserError(
        #                         _(
        #                             "Please assign the Accrual Expense Account for Product - %s.") % line.product_id.name)
        #
        #                 if line.qty_received < line.product_qty:
        #                     line.write({'manual_complete': True})
        #                     credit = credit + ((line.product_qty - line.qty_received) * line.price_unit)
        #                     adjust_credit = (0, 0, {
        #                         'name': line.name or '/',
        #                         'partner_id': rec.partner_id.id,
        #                         'account_id': line.product_id.accrual_account.id,
        #                         'analytic_account_id': line.account_analytic_id.id or False,
        #                         'journal_id': rec.company_id.accrual_journal.id,
        #                         'date': fields.Date.today(),
        #                         'credit': (line.product_qty - line.qty_received) * line.price_unit,
        #                         'debit': 0.0,
        #                     })
        #                     line_ids.append(adjust_credit)
        #             if credit > 0:
        #                 adjust_debit = (0, 0, {
        #                     'name': rec.name or '/',
        #                     'partner_id': rec.partner_id.id,
        #                     'account_id': rec.company_id.accrual_account.id,
        #                     'journal_id': rec.company_id.accrual_journal.id,
        #                     'date': fields.Date.today(),
        #                     'debit': credit,
        #                     'credit': 0.0,
        #                 })
        #                 line_ids.append(adjust_debit)
        #
        #             if len(line_ids) > 0:
        #                 move['line_ids'] = line_ids
        #                 move_id = self.env['account.move'].create(move)
        return res