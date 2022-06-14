from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _create_cut_sequence(self):
        unbuild_vals = []
        for company in self:
            unbuild_vals.append({
                'name': 'Cutting',
                'code': 'mrp.cut',
                'company_id': company.id,
                'prefix': 'CT/',
                'padding': 5,
                'number_next': 1,
                'number_increment': 1
            })
        if unbuild_vals:
            self.env['ir.sequence'].create(unbuild_vals)

    @api.model
    def create_cut_sequence(self):
        company_ids = self.env['res.company'].search([])
        company_has_cutting_seq = self.env['ir.sequence'].search([('code', '=', 'mrp.cut')]).mapped('company_id')
        company_todo_sequence = company_ids - company_has_cutting_seq
        company_todo_sequence._create_cut_sequence()

    def _create_per_company_sequences(self):
        super(ResCompany, self)._create_cut_sequence()
        self._create_cut_sequence()
