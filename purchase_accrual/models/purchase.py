# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    accrual_journal = fields.Many2one('account.journal', string="Accrual Journal")
    accrual_account = fields.Many2one('account.account', string="Accrual Account(B/L)")


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    manual_complete = fields.Boolean('Manual Complete',default=False,copy=False)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('order_line.manual_complete')
    def _get_product_data(self):
        ct = 0
        for line in self.order_line:
            if line.manual_complete is False:
                ct=1
                break
        if ct == 0 :
            self.is_rev_pending = False
        else:
            self.is_rev_pending = True

    @api.depends('move_id','purchase_type')
    def _get_accrual_data(self):
        ct = 0
        for rec in self:
            if not rec.move_id and rec.purchase_type == 'normal':
                self.is_accrual_move_pending = True
            else:
                self.is_accrual_move_pending = False

    move_id = fields.Many2one('account.move','Accrual Move',copy=False)
    is_rev_pending = fields.Boolean('Is Pending',compute='_get_product_data',store=True)
    is_accrual_move_pending = fields.Boolean('Is Accrual Move Pending',compute='_get_accrual_data',store=True)
    purchase_type = fields.Selection([('normal', 'Create Accrual Entry'), ('asset', 'No need Accrual Entry')],required=True)

    def done_purchase_fun(self):
        for rec in self:
            if rec.purchase_type == 'normal':

                line_ids = []
                move = {
                    'name': '/',
                    'journal_id': rec.company_id.accrual_journal.id,
                    'date': fields.Date.today(),
                }
                credit = 0
                if not rec.company_id.accrual_account or not rec.company_id.accrual_journal:
                    raise UserError(
                        _("Please assign the default Accrual values"))
                else:
                    for line in rec.order_line:
                        if not line.product_id.accrual_account:
                            raise UserError(
                                _(
                                    "Please assign the Accrual Expense Account for Product - %s.") % line.product_id.name)

                        if line.qty_received < line.product_qty:
                            line.write({'manual_complete':True})
                            credit = credit + ((line.product_qty-line.qty_received) * line.price_unit)
                            adjust_credit = (0, 0, {
                                'name': line.name or '/',
                                'partner_id': rec.partner_id.id,
                                'account_id': line.product_id.accrual_account.id,
                                'analytic_account_id':line.account_analytic_id.id or False, 
                                'journal_id': rec.company_id.accrual_journal.id,
                                'date': fields.Date.today(),
                                'credit': (line.product_qty-line.qty_received) * line.price_unit,
                                'debit': 0.0,
                            })
                            line_ids.append(adjust_credit)
                    if credit > 0:
                        adjust_debit = (0, 0, {
                            'name': rec.name or '/',
                            'partner_id': rec.partner_id.id,
                            'account_id': rec.company_id.accrual_account.id,
                            'journal_id': rec.company_id.accrual_journal.id,
                            'date': fields.Date.today(),
                            'debit': credit,
                            'credit': 0.0,
                        })
                        line_ids.append(adjust_debit)

                    if len(line_ids)>0:
                        move['line_ids'] = line_ids
                        move_id = self.env['account.move'].create(move)

            return True
    
    def create_accrual(self):
        for rec in self:
                line_ids = []
                move = {
                    'name': '/',
                    'journal_id': rec.company_id.accrual_journal.id,
                    'date': fields.Date.today(),
                }
                if not rec.company_id.accrual_account or not rec.company_id.accrual_journal:
                    raise UserError(
                        _("Please assign the default Accrual values"))
                else:
                    adjust_credit = (0, 0, {
                        'name': rec.name or '/',
                        'partner_id': rec.partner_id.id,
                        'account_id': rec.company_id.accrual_account.id,
                        'journal_id': rec.company_id.accrual_journal.id,
                        'date': fields.Date.today(),
                        'credit': rec.amount_untaxed,
                        'debit': 0.0,
                    })
                    line_ids.append(adjust_credit)

                    for line in rec.order_line:
                        if not line.product_id.accrual_account:
                            raise UserError(
                                _(
                                    "Please assign the Accrual Expense Account for Product - %s.") % line.product_id.name)
                        adjust_debit = (0, 0, {
                            'name': line.name or '/',
                            'partner_id': rec.partner_id.id,
                            'account_id': line.product_id.accrual_account.id,
                            'journal_id': rec.company_id.accrual_journal.id,
                            'analytic_account_id':line.account_analytic_id.id or False, 
                            'date': fields.Date.today(),
                            'debit': line.price_subtotal,
                            'credit': 0.0,
                        })
                        line_ids.append(adjust_debit)

                    move['line_ids'] = line_ids
                    move_id = self.env['account.move'].create(move)
                    rec.write({'move_id': move_id.id})

    # def button_approve(self):
    #     result = super(PurchaseOrder, self).button_approve()
    #     raise UserError(_('TEST'))
    #     if self.purchase_type == 'normal':
    #         self.create_accrual()
        
    #     return result

    def _create_picking(self):
        result = super(PurchaseOrder, self)._create_picking()
        self.create_accrual()
        return result


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    accrual_account = fields.Many2one('account.account', string="Accrual Account(P/L)")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    accrual_move_id = fields.Many2one('account.move', 'Accrual Move')

    def action_done(self):
        result = super(StockPicking, self).action_done()
        if result:
            for rec in self:
                line_ids = []
                move = {
                    'name': '/',
                    'journal_id': rec.company_id.accrual_journal.id,
                    'date': fields.Date.today(),
                }
                if not rec.company_id.accrual_account or not rec.company_id.accrual_journal:
                    raise UserError(
                        _("Please assign the default Accrual values"))
                else:
                    credit = 0
                    for line in rec.move_lines:
                        if not line.product_id.accrual_account:
                            raise UserError(
                                _(
                                    "Please assign the Accrual Expense Account for Product - %s.") % line.product_id.name)

                        else:
                            credit = credit + (line.product_qty*line.purchase_line_id.price_unit)
                            adjust_credit = (0, 0, {
                                    'name': line.product_id.name or '/',
                                    'partner_id': rec.partner_id.id,
                                    'account_id': line.product_id.accrual_account.id,
                                    'analytic_account_id':line.purchase_line_id.account_analytic_id.id or False, 
                                    'journal_id': rec.company_id.accrual_journal.id,
                                    'date': fields.Date.today(),
                                    'credit': line.product_qty*line.purchase_line_id.price_unit,
                                    'debit': 0.0,
                                })
                            line_ids.append(adjust_credit)
                    if credit > 0:
                        adjust_debit = (0, 0, {
                            'name': rec.name or '/',
                            'partner_id': rec.partner_id.id,
                            'account_id': rec.company_id.accrual_account.id,
                            'journal_id': rec.company_id.accrual_journal.id,
                            'date': fields.Date.today(),
                            'debit': credit,
                            'credit': 0.0,
                        })
                        line_ids.append(adjust_debit)

                if len(line_ids)>0:
                    move['line_ids'] = line_ids
                    move_id = self.env['account.move'].create(move)
                    rec.write({'accrual_move_id': move_id.id})
                    for line in rec.purchase_id.order_line:
                        if line.product_qty == line.qty_received:
                            line.write({'manual_complete': True})
                return result
