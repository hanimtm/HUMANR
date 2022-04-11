# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from datetime import datetime
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class City(models.Model):
    _name = 'res.city'
    _description = 'Res City'

    name = fields.Char('City', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)

    _sql_constraints = [
        ('unique_city_name', 'UNIQUE(name, country_id)', 'A city with this name is already in system!'),
    ]


class CityAirfare(models.Model):
    _name = 'city.airfare'
    _rec_name = 'country_id'
    _description = 'City AirFare'

    city_id = fields.Many2one('res.city', string='City')
    country_id = fields.Many2one('res.country', string='Country', required=True)
    adult_fare = fields.Float('Adult Fare', required=True, help="This amount shows return fare from the selected city.")
    child_fare = fields.Float('Child Fare', compute='_get_child_fare', help="80% of Adult Fare")
    infant_fare = fields.Float('Infant Fare', compute='_get_child_fare', help="12.5% of Adult Fare")

    _sql_constraints = [
        ('unique_city_fare', 'UNIQUE(country_id)', 'A fare for this country already in system!'),
    ]

    @api.depends('adult_fare')
    def _get_child_fare(self):
        """
            calculate the child and infant fare
        """
        for rec in self:
            rec.child_fare = 0.0
            rec.infant_fare = 0.0
            if rec.adult_fare > 0:
                #rec.child_fare = (rec.adult_fare * 80) / 100
                #rec.infant_fare = (rec.adult_fare * 12.5) / 100
                rec.child_fare = (rec.adult_fare)
                rec.infant_fare = (rec.adult_fare)

    @api.onchange('country_id')
    def onchange_country(self):
        """
            onchange the value based on selected country,
            city
        """
        res = {'domain': {}}
        self.city_id = False
        if not self.country_id:
            res['domain'].update({'city_id': [('id', 'in', [])]})
            return res
        city_ids = self.env['res.city'].search([('country_id', '=', self.country_id.id)])
        res['domain'].update({'city_id': [('id', 'in', [city.id for city in city_ids])]})
        return res


class HrContract(models.Model):
    _name = 'hr.contract'
    _description = 'Employee Contract'
    _inherit = ['mail.thread', 'hr.contract']

    @api.depends('employee_id')
    def _get_total_members(self):
        """
            calculate the adults, children and infant
        """
        for rec in self:
            #rec.adults = 1
            rec.adults = 0
            rec.children = 0
            rec.infant = 0
            adults = 0
            children = infant = 0
            if rec.employee_id:
                for dependent in rec.employee_id.dependent_ids:
                    current_year = datetime.today().strftime('%Y')
                    dob_year = datetime.strptime(str(dependent.birthdate), DEFAULT_SERVER_DATE_FORMAT).year
                    age_year = int(current_year) - int(dob_year)
                    # if age_year > 18 and dependent.adults < 2:
                    #     adults += 1
                    # elif age_year >= 2 and age_year < 18 and children < 2:
                    #     children += 1
                    # elif age_year < 2 and infant < 2:
                    #     infant += 1
                    if dependent.relation == 'spouse':
                        adults += 1
                    elif dependent.relation == 'child' and age_year < 18:
                        children += 1
                    # elif age_year < 2:
                    #      infant += 1

                rec.adults = adults
                rec.children = children
                # rec.infant = infant
                # Below hack is for contract calculation, if employee will have 2 children then he will not get fare for infant
                # if children == 2:
                #     rec.infant = 0

    air_allowance = fields.Boolean('Eligible for Ticket Allowance')
    air_destination = fields.Many2one('city.airfare', 'Vacation Destination',
                                      help="Return ticket fare from employees home town")
    employee_ticket = fields.Integer('Employee',default=1,readonly=True)
    adults = fields.Integer('Adult(s)', compute='_get_total_members', help='Employee and Spouse')
    children = fields.Integer('Children', compute='_get_total_members',
                              help='Maximum two children, if no infants(Age must be between 2 to 18)')
    infant = fields.Integer('Infant(s)', compute='_get_total_members',
                            help='Maximum two infants, if no children(Below 2 Years)')
    company_pay_children = fields.Integer('Company Pay (Children)')
    company_pay_adult = fields.Integer('Company Pay (Adult)')
    reentry_cost = fields.Float('Re-Entry Cost')
    ticket_total = fields.Float('Ticket Total')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)

    @api.onchange('infant', 'children', 'adults','air_destination','air_allowance')
    def onchange_data(self):
        for contract in self:
            destination = self.env['city.airfare'].search([('country_id','=',contract.employee_id.country_id.id)],limit=1).id
            contract.air_destination = self.env['city.airfare'].search([('country_id','=',contract.employee_id.country_id.id)],limit=1)
            print('%s',destination)
            contract.company_pay_adult = 0
            if contract.adults > 0 :
                contract.company_pay_adult = 1

            contract.company_pay_children = 0
            if contract.children > 0 and contract.children <= 2:
                contract.company_pay_children = contract.children
            elif contract.children > 2:
                contract.company_pay_children = 2

    @api.onchange('air_destination','air_allowance','reentry_cost','company_pay_children','company_pay_adult')
    def onchange_ticket(self):
        for contract in self:
            if self.air_allowance:
                contract.ticket_total = ((contract.employee_ticket*contract.air_destination.adult_fare)+(contract.company_pay_adult*contract.air_destination.adult_fare)+(contract.company_pay_children*contract.air_destination.child_fare) + contract.reentry_cost)