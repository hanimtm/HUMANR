# -*- coding: utf-8 -*-

from odoo import models, fields, api,exceptions
from datetime import datetime, timedelta
import odoo.addons.decimal_precision as dp
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.translate import _


class hr_travel_request(models.Model):
    _name = 'hr.travel.request'
    _inherit = ['mail.thread']
    _description = 'Travel Request'
    _order = 'start_date desc, employee_id'

    @api.model
    def _get_employee_from_uid(self):
        """
        Default value of employee_id is the employee of current user.
        """
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self._uid)], limit=1, order='id'
        )
        return employee.id

    # Columns
    name = fields.Char(string='Summary', required=True, readonly=True,
                       size=128, states={'draft': [('readonly', False)]})
    hr_travel_type_id = fields.Many2one(
        comodel_name='hr.travel.type', string='Travel Type',
        required=True, readonly=True, ondelete='restrict',
        states={'draft': [('readonly', False)]}
    )
    start_date = fields.Date(string='Start Date', required=True, readonly=True,
                             states={'draft': [('readonly', False)]})
    end_date = fields.Date(string='End Date', required=True, readonly=True,
                           states={'draft': [('readonly', False)]})
    duration = fields.Float('Number Of Days', readonly=True)
    employee_id = fields.Many2one(
        comodel_name='hr.employee', string='Employee',
        required=True, readonly=True, ondelete='restrict',
        states={'draft': [('readonly', False)]},
        default=_get_employee_from_uid
    )
    employee_department_id = fields.Many2one(
        comodel_name='hr.department', string='Department',
        readonly=True, states={'draft': [('readonly', False)]}
    )
    employee_designation_id = fields.Many2one(
        comodel_name='hr.job', string='Designation',
        required=True, readonly=True,
        states={'draft': [('readonly', False)]}
    )
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('confirm', 'Confirmed'),
                   ('refuse', 'Refused'), ('approved', 'Approved')],
        string='Status', default='draft'
    )
    visa_expiry_date = fields.Date(string='Visa Expiry Date', readonly=True,
                                   states={'draft': [('readonly', False)]})
    mutiple_visit_visa = fields.Boolean(
        string='Multiple Visit Visa', readonly=True,
        states={'draft': [('readonly', False)]}, default=False
    )
    destination_id = fields.Many2one(
        comodel_name='res.country', string='Destination',
        readonly=True, states={'draft': [('readonly', False)]}
    )
    round_trip = fields.Boolean(
        string='Round Trip', readonly=True, default=False,
        states={'draft': [('readonly', False)]}
    )
    one_way_trip = fields.Boolean(
        string='One Way Trip', readonly=True, default=False,
        states={'draft': [('readonly', False)]}
    )
    ticket_price = fields.Float(
        string='Ticket Price', readonly=True,
        digits_compute=dp.get_precision('Payroll'),
        states={'draft': [('readonly', False)]}
    )
    visa_cost = fields.Float(
        string='Visa / Re-Entry Cost', readonly=True,
        digits_compute=dp.get_precision('Payroll'),
        states={'draft': [('readonly', False)]}
    )
    general_description = fields.Text(string='Description', readonly=True,
                                      states={'draft': [('readonly', False)]})
    attachments_count = fields.Integer(string="Documents Count")

    travellers = fields.Selection(
        selection=[('employee', 'Employee Only'), ('employee_dependent', 'Employee & Dependants'),
                   ('dependent', 'Dependants Only')],
        states={'draft': [('readonly', False)]},
        string='Travellers',required=True
    )

    dependents = fields.Many2many('employee.dependent','ticket_dependent_rel',string='Dependents',
                                  states={'draft': [('readonly', False)]})
    request_type = fields.Selection(
        selection=[('ticket', 'Ticket Only'), ('ticket_reentry', 'Ticket & Re-Entry'),
                   ('reentry', 'Re-Entry Only')],
        states={'draft': [('readonly', False)]},
        string='Request Type',required=True
    )

    leave_id = fields.Many2one('hr.holidays','Leave')

    # @api.onchange('travellers','employee_id')
    # def onchange_travellers(self):
    #     for travel in self:
    #         if travel.travellers and travel.travellers != 'employee':
    #             travel.travellers = self.env['employee.dependent'].search([('employee_id','=',travel.employee_id.id)]).ids

    # @api.model
    # def create(self, vals):
    #     line = super(hr_travel_request, self).create(vals)
    #     if line.leave_id:
    #         line.leave_id.ticket_id = self.id
    #     return line

    @api.onchange('dependents','employee_id','travellers','request_type')
    def onchange_dependents(self):
        for travel in self:
            contract_ids = self.env['hr.contract'].search(
                [('employee_id', '=', travel.employee_id.id), ('state', '=', 'open')])
            if len(contract_ids) > 1:
                raise exceptions.ValidationError(_('Employee Must Have Only One Running Contract'))
            if len(contract_ids) < 1:
                raise exceptions.ValidationError(_('Employee Must Have One Running Contract'))

            # adult = contract_ids.adults * contract_ids.air_destination.adult_fare
            # children = contract_ids.children * contract_ids.air_destination.child_fare
            # infant = contract_ids.infant * contract_ids.air_destination.infant_fare
            if travel.travellers == 'employee':
                travel.ticket_price = 0
                travel.ticket_price = 1 * contract_ids.air_destination.adult_fare
            elif travel.travellers == 'employee_dependent':
                adults = 1
                children = infant = 0
                travel.ticket_price = 0
                for dependent in travel.dependents:
                    current_year = datetime.today().strftime('%Y')
                    dob_year = datetime.strptime(str(dependent.birthdate), DF).year
                    age_year = int(current_year) - int(dob_year)
                    if age_year >= 18:
                        adults += 1
                    elif age_year >= 2 and age_year < 18 and children < 2:
                        children += 1
                    elif age_year < 2 and infant < 2:
                        infant += 1
                travel.ticket_price = ((adults * contract_ids.air_destination.adult_fare) + (
                            children * contract_ids.air_destination.child_fare) + (
                             infant * contract_ids.air_destination.infant_fare))
            elif travel.dependents == 'dependentee':
                travel.ticket_price = 0
                adults = children = infant = 0
                for dependent in travel.dependents:
                    current_year = datetime.today().strftime('%Y')
                    dob_year = datetime.strptime(str(dependent.birthdate), DF).year
                    age_year = int(current_year) - int(dob_year)
                    if age_year >= 18:
                        adults += 1
                    elif age_year >= 2 and age_year < 18 and children < 2:
                        children += 1
                    elif age_year < 2 and infant < 2:
                        infant += 1
                travel.ticket_price = ((adults * contract_ids.air_destination.adult_fare) + (
                        children * contract_ids.air_destination.child_fare) + (
                                               infant * contract_ids.air_destination.infant_fare))
            if travel.request_type == 'reentry':
                travel.ticket_price = 0


    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        """
        Travel request start date must be less than end date.
        """
        msg = _('Travel request start date must be less than end date.')
        for travel_request in self:
            if travel_request.start_date\
                    and travel_request.end_date\
                    and travel_request.start_date > travel_request.end_date:
                raise Warning(msg)
        return True

    def button_reset_to_draft(self):
        """
        Reset refused travel requests to draft.
        """
        self.state = 'draft'
        return True

    def button_confirm(self):
        """
        This function opens a window to compose an email,
        with the travel request template message loaded by default.
        """
        self.state = 'confirm'
        mdata_obj = self.env['ir.model.data']
        try:
            template_id = self.env.ref(
                'trobz_hr_travel_request.email_template_confirm_travel_request'
            )
        except ValueError:
            template_id = False
        try:
            compose_form_id = self.env.ref(
                'trobz_hr_travel_request.'
                'travel_request_email_compose_message_wizard_form'
            )
        except ValueError:
            compose_form_id = False
        ctx = dict(self._context)
        ctx.update({
            'default_model': 'hr.travel.request',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id and template_id.id or False),
            'default_template_id': template_id and template_id.id or False,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id and compose_form_id.id or False, 'form')],
            'view_id': compose_form_id and compose_form_id.id or False,
            'target': 'new',
            'context': ctx,
        }

    def button_approve(self):
        """
        This function opens a window to compose an email,
        with the travel request template message loaded by default
        """
        self.state = 'approved'
        move = {
            'name': '/',
            'journal_id': self.company_id.accrual_journal.id,
            'date': fields.Date.today(),
        }
        line_ids = []
        credit_account = int(self.env['ir.config_parameter'].sudo().get_param('ticket_debit_account'))
        debit_account = int(self.env['ir.config_parameter'].sudo().get_param('ticket_credit_account'))

        if debit_account and credit_account:
            adjust_credit = (0, 0, {
                'name': self.employee_id.name or '/ ' + 'Ticket Reverse Accrual',
                'partner_id': self.employee_id.address_home_id.id,
                'account_id': credit_account,
                'journal_id': self.company_id.accrual_journal.id,
                'date': fields.Date.today(),
                'debit': self.ticket_price + self.visa_cost,
                'credit': 0.0,
            })
            line_ids.append(adjust_credit)
            adjust_debit = (0, 0, {
                'name': self.employee_id.name or '/ ' + 'EOS',
                'partner_id': self.employee_id.address_home_id.id,
                'account_id': debit_account,
                'journal_id': self.company_id.accrual_journal.id,
                'analytic_account_id': self.analytic_account_id.id or False,
                'date': fields.Date.today(),
                'credit': self.ticket_price + self.visa_cost,
                'debit': 0.0,
            })
            line_ids.append(adjust_debit)

            move['line_ids'] = line_ids
            move_id = self.env['account.move'].create(move)
            accrual = {
                'move_id': move_id.id,
                'employee_id': self.employee_id.id,
                'date': fields.Date.today(),
                'type': 'reverse',
            }
            self.env['employee.accrual.move'].sudo().create(accrual)
            contracts = self.employee_id.get_active_contracts(date=fields.Date.today())

            for cont in contracts:
                print('Contracts %s : ', contracts)
                cont.reentry_cost = cont.reentry_cost - self.visa_cost
                cont.ticket_total = cont.ticket_total - (self.ticket_price + self.visa_cost)
        try:
            template_id = self.env.ref(
                'ahcec_hr_travel_request.email_template_approved_travel_request'
            )
        except ValueError:
            template_id = False
        try:
            compose_form_id = self.env.ref(
                'ahcec_hr_travel_request.'
                'travel_request_email_compose_message_wizard_form'
            )
        except ValueError:
            compose_form_id = False
        ctx = dict(self._context)
        ctx.update({
            'default_model': 'hr.travel.request',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id and template_id.id or False),
            'default_template_id': template_id and template_id.id or False,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id and compose_form_id.id or False, 'form')],
            'view_id': compose_form_id and compose_form_id.id or False,
            'target': 'new',
            'context': ctx,
        }

    def button_refuse(self):
        """
        This function opens a window to compose an email,
        with the travel request template message loaded by default.
        """
        self.state = 'refuse'
        try:
            template_id = self.env.ref(
                'trobz_hr_travel_request.email_template_refused_travel_request'
            )
        except ValueError:
            template_id = False
        try:
            compose_form_id = self.env.ref(
                'trobz_hr_travel_request.'
                'travel_request_email_compose_message_wizard_form'
            )
        except ValueError:
            compose_form_id = False
        ctx = dict(self._context)
        ctx.update({
            'default_model': 'hr.travel.request',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id and template_id.id or False),
            'default_template_id': template_id and template_id.id or False,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id and compose_form_id.id or False, 'form')],
            'view_id': compose_form_id and compose_form_id.id or False,
            'target': 'new',
            'context': ctx,
        }

    @api.onchange('employee_id')
    def on_change_employee(self):
        """
        @param employee_id: selected employee
        @return:
            employee_department_id
            employee_designation_id
        """
        if not self.employee_id:
            self.employee_department_id = False
            self.employee_designation_id = False
            return
        job_id = self.employee_id.job_id\
            and self.employee_id.job_id.id or False
        department_id = self.employee_id.department_id\
            and self.employee_id.department_id.id or False
        self.employee_department_id = department_id
        self.employee_designation_id = job_id

    @api.onchange('round_trip')
    def on_change_round_trip(self):
        """
        Be able to choose one_way_trip or round_trip,
        not both of them at a time.
        """
        self.one_way_trip = not self.round_trip and True or False

    @api.onchange('one_way_trip')
    def on_change_one_way_trip(self):
        """
        Be able to choose one_way_trip or round_trip,
        not both of them at a time.
        """
        self.round_trip = not self.one_way_trip and True or False

    @api.model
    def calculate_duration(self, employee_id, start_date, end_date):
        """
        Having start_date and end_date, calculating the days between them
        based on the contract of the employee.
        """
        if not start_date\
                or not end_date:
            return 0
        contract_obj = self.env['hr.contract']
        contracts = contract_obj.search(
            [('employee_id', '=', employee_id),('state','=','open')],
            order='date_start', limit=1
        )
        if not contracts:
            return 0
        # resource_calendar = contracts and contracts.working_hours and contracts.working_hours[0] or False
        # if not resource_calendar:
        #     return 0

        duration = 0
        dt_start_date = datetime.strptime(start_date, DF)
        dt_end_date = datetime.strptime(end_date, DF)
        delta = dt_end_date - dt_start_date
        work_days = []
        # rca_obj = self.env['resource.calendar.attendance']
        # resource_calendar_attendances = rca_obj.search(
        #     [('calendar_id', '=', resource_calendar.id)]
        # )
        # for rca in resource_calendar_attendances:
        #     dayofweek = rca and rca.dayofweek and rca.dayofweek[0] or False
        #     work_days.append(str(dayofweek))
        for day in range(delta.days + 1):
            next_date = dt_start_date + timedelta(days=day)
            # if not working schedule and not in Saturday and Sunday
            #if not resource_calendar\
            if next_date.weekday() not in (5, 6):
                duration += 1
            elif str(next_date.weekday()) in work_days:
                duration += 1
        return duration

    @api.onchange('start_date', 'end_date', 'employee_id')
    def on_change_date_value(self):
        """
        @param start_date: selected
        @param end_date: selected
        @return: duration: number of days from start_date to end_date
        """
        self.duration = self.calculate_duration(
            self.employee_id.id, self.start_date, self.end_date
        )
        return

    def act_view_attachments(self):
        """
        View the list of documents associated with the travel request
        """
        attachment_obj = self.env['ir.attachment']
        attachments = attachment_obj.search(
            [('res_model', '=', 'hr.travel.request'),
             ('res_id', 'in', self.ids)]
        )
        if attachments:
            return {
                'domain': [('id', 'in', attachments.ids)],
                'name': _('Documents'),
                'view_mode': 'tree,form',
                'res_model': 'ir.attachment',
                'type': 'ir.actions.act_window',
                'context': self._context,
            }
        raise Warning(_("This request does not contain any documents!"))

    @api.model
    def create(self, vals):
        """
        From three info: employee, start date and end date,
        compute the duration of each leave request.
        """
        if 'employee_id' in vals\
                and 'start_date' in vals\
                and 'end_date' in vals:
            vals.update({'duration': self.calculate_duration(
                vals['employee_id'], vals['start_date'],
                vals['end_date']
            )})
        return super(hr_travel_request, self).create(vals)

    def write(self, vals):
        """
        From three info: employee, start date and end date,
        compute the duration of each leave request.
        """
        res = super(hr_travel_request, self).write(vals)
        if 'employee_id' in vals\
                or 'start_date' in vals\
                or 'end_date' in vals:
            for request in self:
                request.duration = self.calculate_duration(
                    request.employee_id.id, request.start_date,
                    request.end_date
                )
        return res

hr_travel_request()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
