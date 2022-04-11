# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import string

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import time

import calendar


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _order = 'id desc'

    insurance_ids = fields.One2many('insurance.details', 'employee_id', string='Medical Insurance')


class EmployeeClass(models.Model):
    _name = 'employee.class'
    _description = 'Employee Class'

    name = fields.Char('Name', required=True)


class InsuranceDetails(models.Model):
    _name = 'insurance.details'
    _inherit = 'mail.thread'
    _order = 'id desc'
    _description = 'Employee Medical Insurance'

    def _add_followers(self):
        for insurance in self:
            if insurance.employee_id.user_id:
                insurance.message_subscribe_users(user_ids=insurance.employee_id.user_id.id)

    def _count_claim(self):
        """
            count the number of claims
        """
        for insurance in self:
            insurance.claim_count = len(insurance.claims_ids)

    name = fields.Char(string="Insurance Number", required=True, track_visibility='onchange')
    card_code = fields.Char('Card Code')
    member_name = fields.Char('Member Name', compute='_get_employee_vals')
    note = fields.Text('Note')
    claim_count = fields.Integer(string='# of claims', compute=_count_claim)
    insurance_amount = fields.Float('Insurance Amount', required=True, track_visibility='onchange')
    premium_amount = fields.Float('Premium Amount / Day ', required=True, track_visibility='onchange')
    start_date = fields.Date('Start Date', required=True, default=datetime.today(), track_visibility='onchange')
    end_date = fields.Date('End Date', required=True, track_visibility='onchange')
    dob = fields.Date('Date of Birth', compute='_get_employee_vals', store=True)
    premium_type = fields.Selection([('monthly', 'Monthly'),
                                     ('quarterly', 'Quarterly'),
                                     ('half', 'Half Yearly'),
                                     ('yearly', 'Yearly')], string='Payment Mode', required=True, default='monthly',
                                    track_visibility='onchange')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirm'),
                              ('cancelled', 'Cancel'),
                              ('done', 'Done')], string='Status', default='draft', track_visibility='onchange')

    class_id = fields.Many2one('employee.class', string='Class', track_visibility='onchange')
    gender = fields.Selection([('male', 'Male'),
                               ('female', 'Female')], compute='_get_employee_vals', store=True)
    relation = fields.Selection([('employee', 'Employee'),
                                 ('child', 'Child'),
                                 ('spouse', 'Spouse')], track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee', required=True, string='Employee', track_visibility='onchange')
    supplier_id = fields.Many2one('res.partner', required=True, string='Supplier', domain=[('supplier', '=', True)],
                                  track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', compute='_get_employee_vals', store=True)
    responsible_id = fields.Many2one('res.users', string='Responsible', required=True,
                                     default=lambda self: self.env.uid,
                                     track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', compute='_get_employee_vals', store=True,
                                 track_visibility='onchange')
    claims_ids = fields.One2many('claim.details', 'insurance_id', string='Claims')
    premium_ids = fields.One2many('insurance.premium', 'insurance_id', string='Insurance premium')
    dependent_ids = fields.One2many('insurance.employee.dependent', 'insurance_id', string='Dependents')
    is_invoice_created = fields.Boolean('Invoice Created', readonly=True)

    @api.depends('employee_id')
    def _get_employee_vals(self):
        for insurance in self:
            # if insurance.employee_id:
            insurance.dob = insurance.employee_id.sudo().birthday
            insurance.gender = insurance.employee_id.sudo().gender
            insurance.company_id = (
                insurance.employee_id.company_id and insurance.employee_id.company_id.id or False) or (
                insurance.env.user.company_id and insurance.env.user.company_id.id or False)
            insurance.currency_id = insurance.company_id and insurance.company_id.currency_id and insurance.company_id.currency_id.id or False
            insurance.member_name = insurance.employee_id.sudo().name

    @api.constrains('insurance_amount', 'premium_amount')
    def check_premium_amount(self):
        """
            Check premium amount is less than insurance amount or not
        """
        for insurance in self:
            if insurance.insurance_amount < insurance.premium_amount:
                raise ValidationError(_('Insurance amount must be greater then premium amount!'))

    @api.model
    def create(self, values):
        # values['name'] = self.env['ir.sequence'].next_by_code('insurance.details')
        res = super(InsuranceDetails, self).create(values)
        if values.get('employee_id'):
            res._add_followers()
        return res

    def write(self, values):
        res = super(InsuranceDetails, self).write(values)
        if values.get('employee_id'):
            self._add_followers()
        return res

    @api.onchange('insurance_amount', 'start_date', 'end_date', )
    def onchange_insurance_amount(self):
        for insurance in self:
            if insurance.start_date and insurance.end_date:
                from_date = datetime.strptime(str(insurance.start_date), '%Y-%m-%d')
                start = datetime.date(from_date)
                end_date = datetime.strptime(str(insurance.end_date), '%Y-%m-%d')
                end = datetime.date(end_date)
                days = abs(end - start).days + 1
                insurance.premium_amount = insurance.insurance_amount / days

    def create_invoice(self):
        """
            Create Invoice for Premium Amount
        """
        product_id = self.env.ref('ahcec_hr_medical.insurance_prodcuct')
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']

        if not self.supplier_id.property_account_payable_id:
            raise UserError(
                _('There is no payable account defined for this supplier: "%s".') %
                (self.supplier_id.name,))

        # Create Invoice
        default_fields = invoice_obj.fields_get()
        inv_default = invoice_obj.default_get(default_fields)
        inv_default.update({'partner_id': self.supplier_id.id,
                            'date_invoice': fields.Date.today(),
                            'type': 'in_invoice',
                            'origin': self.name,
                            'date_due': fields.Date.today(),
                            'account_id': self.supplier_id.property_account_payable_id.id})

        invoices_id = invoice_obj.create(inv_default)
        invoices_id._onchange_partner_id()

        # Create Invoice Lines
        line_default_fields = invoice_line_obj.fields_get()
        inv_line_val = invoice_line_obj.default_get(line_default_fields)
        inv_line_val.update({'name': product_id.name,
                             'product_id': product_id.id,
                             'price_unit': self.insurance_amount,
                             'invoice_id': invoices_id.id,
                             'account_id': (
                                                   product_id.property_account_expense_id and product_id.property_account_expense_id.id or False) or (
                                                   product_id.categ_id.property_account_expense_categ_id and product_id.categ_id.property_account_expense_categ_id.id or False)})

        invoices_line_id = invoice_line_obj.create(inv_line_val)
        invoices_line_id._onchange_product_id()
        self.invoice_id = (invoices_id and invoices_id.id or False)
        self.is_invoice_created = True

    @api.onchange('company_id')
    def onchange_company_id(self):
        """
            Set currency: Value from Company
        """
        self.currency_id = False
        if self.company_id:
            self.currency_id = self.company_id.currency_id and self.company_id.currency_id.id or False

    # @api.onchange('premium_type', 'start_date', 'end_date', 'insurance_amount')
    # def onchange_premium(self):
    #     self.generate_premiums()
    #     return True
    def generate_premiums(self):
        self.ensure_one()
        for insurance in self:
            if insurance.start_date and insurance.end_date and insurance.premium_type:
                insurance.premium_ids.unlink()
                premium_list = []
                f_date = datetime.strptime(str(insurance.start_date), '%Y-%m-%d')
                next_date = datetime.date(f_date)
                index = 1
                e_date = datetime.strptime(str(insurance.end_date), '%Y-%m-%d')
                end_date = datetime.date(e_date)
                # start = datetime.date(next_date)
                # end = datetime.date(end_date)
                # days = abs(end - start).days + 1

                months = (abs(end_date.year - next_date.year) * 12 + (end_date.month - next_date.month)) + 1

                while next_date <= end_date:
                    if index != months:
                        month_days = calendar.monthrange(next_date.year, next_date.month)[1]
                        this_month_day = month_days - next_date.day + 1
                    else:
                        this_month_day = end_date.day

                    amount = (insurance.premium_amount * this_month_day)

                    premium_list.append({'sequence': index,
                                         'date': next_date,
                                         'amount': amount or 0.0,
                                         'is_invoice_created': False
                                         })
                    if insurance.premium_type == 'monthly':
                        # next_date = next_date + relativedelta(months=1)
                        next_date = date(next_date.year, next_date.month, 1) + relativedelta(months=1)
                    elif insurance.premium_type == 'quarterly':
                        next_date = date(next_date.year, next_date.month, 1) + relativedelta(months=3)
                    elif insurance.premium_type == 'half':
                        next_date = date(next_date.year, next_date.month, 1) + relativedelta(months=6)
                    else:
                        next_date = date(next_date.year, next_date.month, 1) + relativedelta(months=12)
                    index += 1
                final_list = [(0, 0, line) for line in premium_list]
                insurance.premium_ids = final_list

    def action_cancelled(self):
        """
            set insurance status as 'cancelled'
        """
        self.ensure_one()
        self.state = 'cancelled'

    def action_confirm(self):
        """
            set insurance status as 'confirmed'
        """
        self.ensure_one()
        self.state = 'confirmed'
        self.generate_premiums()

    def action_done(self):
        """
            set insurance status as 'done'
        """
        self.ensure_one()
        self.state = 'done'

    def action_set_to_draft(self):
        """
            set insurance status as 'draft'
        """
        self.ensure_one()
        self.state = 'draft'

    def view_insurance(self):
        """
           Redirect On Employee Insurance Form
        """
        self.ensure_one()
        form_view = self.env.ref('ahcec_hr_medical.insurance_details_form_view')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Insurance'),
            'res_model': 'insurance.details',
            'view_mode': 'from',
            'views': [(form_view.id, 'form')],
            'res_id': self.id,
            'context': self.env.context,
            'create': False,
            'editable': False,
        }

    def view_claims(self):
        """
           Redirect On Insurance Claim
        """
        self.ensure_one()
        if self.claims_ids:
            tree_view = self.env.ref('ahcec_hr_medical.claims_details_tree_view')
            form_view = self.env.ref('ahcec_hr_medical.claim_details_form_view')
            return {
                'type': 'ir.actions.act_window',
                'name': _('Claims'),
                'res_model': 'claim.details',
                'view_mode': 'form',
                'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
                'domain': [('id', 'in', self.claims_ids.ids)],
                'res_id': self.claims_ids.ids,
                'context': self.env.context,
            }

    @api.model
    def check_insurance_expiry(self):
        """
            Send mail for Insurance Expiry
        """
        template_id = self.env.ref('ahcec_hr_medical.hr_medical_insurance_expiration_email')
        for insurance in self.search([('state', '=', 'confirmed')]):
            reminder_date = datetime.strptime(str(insurance.end_date), DEFAULT_SERVER_DATE_FORMAT) - timedelta(days=10)
            today_date = datetime.strptime(str(fields.Date.today()), DEFAULT_SERVER_DATE_FORMAT)
            if reminder_date == today_date and template_id:
                template_id.send_mail(insurance.id, force_send=True, raise_exception=True)


class InsurancePremium(models.Model):
    _name = 'insurance.premium'
    _rec_name = 'insurance_id'

    sequence = fields.Integer('Sequence', required=True)
    date = fields.Date('Premium Date', required=True)
    amount = fields.Float('Premium Amount', required=True)
    is_move_created = fields.Boolean('Move Created')
    insurance_id = fields.Many2one('insurance.details', string='Insurance')
    # invoice_id = fields.Many2one('account.invoice', string="Invoice")
    move_id = fields.Many2one('account.move', string="Move ID")
    is_invoice_created = fields.Boolean(related='insurance_id.is_invoice_created')

    def view_invoice_action(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views': [(self.env.ref('account.invoice_supplier_form').id, 'form')],
            'res_id': self.invoice_id.id
        }

    def print_invoice(self):
        return self.env.ref('account.account_invoices').report_action(self.invoice_id)

    def action_move_create(self):
        premiums = self.search([('insurance_id.state', '=', 'confirmed'), ('is_move_created', '=', False),
                                ('date', '=', fields.date.today())])
        for premium in premiums:
            premium.create_move()

    # def create_move(self):
    #     for rec in self:
    #         line_ids = []
    #         move = {
    #             'name': '/',
    #             'journal_id': rec.company_id.accrual_journal.id,
    #             'date': fields.Date.today(),
    #         }
    #         if not rec.company_id.accrual_account or not rec.company_id.accrual_journal:
    #             raise UserError(
    #                 _("Please assign the default Accrual values"))
    #         else:
    #             adjust_credit = (0, 0, {
    #                 'name': rec.name or '/',
    #                 'partner_id': rec.partner_id.id,
    #                 'account_id': rec.company_id.accrual_account.id,
    #                 'journal_id': rec.company_id.accrual_journal.id,
    #                 'date': fields.Date.today(),
    #                 'credit': rec.amount_untaxed,
    #                 'debit': 0.0,
    #             })
    #             line_ids.append(adjust_credit)
    #
    #             for line in rec.order_line:
    #                 if not line.product_id.accrual_account:
    #                     raise UserError(
    #                         _(
    #                             "Please assign the Accrual Expense Account for Product - %s.") % line.product_id.name)
    #                 adjust_debit = (0, 0, {
    #                     'name': line.name or '/',
    #                     'partner_id': rec.partner_id.id,
    #                     'account_id': line.product_id.accrual_account.id,
    #                     'journal_id': rec.company_id.accrual_journal.id,
    #                     'date': fields.Date.today(),
    #                     'debit': line.price_subtotal,
    #                     'credit': 0.0,
    #                 })
    #                 line_ids.append(adjust_debit)
    #
    #             move['line_ids'] = line_ids
    #             move_id = self.env['account.move'].create(move)
    #             rec.write({'move_id': move_id.id})
    #         return True


class ClaimDetails(models.Model):
    _name = 'claim.details'
    _inherit = 'mail.thread'

    name = fields.Char(string="Claim Number", required=True)
    date_applied = fields.Date('Date Applied', default=datetime.today(), required=True, track_visibility='onchange')
    claim_amount = fields.Float('Claim Amount', required=True, track_visibility='onchange')
    passed_amount = fields.Float('Passed Amount', track_visibility='onchange')
    insurance_id = fields.Many2one('insurance.details', string='Insurance', required=True,
                                   domain=[('state', '=', 'confirmed')], track_visibility='onchange')
    company_id = fields.Many2one('res.company', string="Company", related='insurance_id.company_id',
                                 track_visibility='onchange')
    responsible_id = fields.Many2one('res.users', string="Responsible", required=True,
                                     default=lambda self: self.env.uid, track_visibility='onchange')
    currency_id = fields.Many2one('res.currency')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirmed'),
                              ('refuse', 'Refused'),
                              ('cancel', 'Cancelled'),
                              ('done', 'Done')], default='draft', track_visibility='onchange')
    note = fields.Text('Note')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)

    def _add_followers(self):
        for claim in self:
            if claim.employee_id.user_id:
                claim.message_subscribe_users(user_ids=claim.employee_id.user_id.id)

    @api.model
    def create(self, values):
        res = super(ClaimDetails, self).create(values)
        if values.get('employee_id'):
            res._add_followers()
        return res

    def write(self, values):
        res = super(ClaimDetails, self).write(values)
        if values.get('employee_id'):
            self._add_followers()
        return res

    @api.onchange('insurance_id')
    def onchange_insurance_id(self):
        """
            Set Responsible: Value from Insurance
        """
        self.responsible_id = False
        if self.insurance_id:
            self.responsible_id = self.insurance_id.responsible_id and self.insurance_id.responsible_id or False
            self.employee_id = self.insurance_id.employee_id.id

    @api.onchange('company_id')
    def onchange_company_id(self):
        """
            Set Currency: Value from Company
        """
        self.currency_id = False
        if self.company_id:
            self.currency_id = self.company_id.sudo().currency_id and self.company_id.currency_id.id or False

    def action_confirm(self):
        """
            set claim status as 'confirm'
        """
        self.ensure_one()
        self.state = 'confirm'

    def action_refuse(self):
        """
            set claim status as 'refuse'
        """
        self.ensure_one()
        self.state = 'refuse'

    def action_cancel(self):
        """
            set claim status as 'cancel'
        """
        self.ensure_one()
        self.state = 'cancel'

    def action_done(self):
        """
            set claim status as 'done'
        """
        self.ensure_one()
        if self.passed_amount <= 0:
            raise UserError(_('Passed Amount should be greater then 0'))
        else:
            self.state = 'done'

    def action_set_to_draft(self):
        """
            set claim status as 'draft'
        """
        self.ensure_one()
        self.state = 'draft'


class InsuranceEmployeeDependent(models.Model):
    _name = 'insurance.employee.dependent'
    _description = 'Employee dependent insurance information'

    @api.depends('name')
    def _get_employee_value(self):
        for insurance in self:
            if insurance.name:
                insurance.dob = insurance.name.sudo().birthdate or False
                insurance.relation = insurance.name.sudo().relation or False

    insurance_id = fields.Many2one('insurance.details', 'Insurance', required=True, ondelete="cascade")
    name = fields.Many2one('employee.dependent', 'Dependent', required=True)
    card_code = fields.Char('Card Code')
    dob = fields.Date('Date of Birth', compute=_get_employee_value, store=True)
    state = fields.Selection(string='Status', related='insurance_id.state')
    gender = fields.Selection([('male', 'Male'),
                               ('female', 'Female')], store=True)
    relation = fields.Selection([('child', 'Child'),
                                 ('spouse', 'Spouse')], track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', related='insurance_id.company_id')
    employee_id = fields.Many2one('hr.employee', string='Employee', related='insurance_id.employee_id')
