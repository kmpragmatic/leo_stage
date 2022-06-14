from odoo import fields, models, api


class MrpCutLine(models.Model):
    _name = 'mrp.cut.line'
    _description = 'Cutting Line'

    company_id = fields.Many2one('res.company', string='Compañia', default=lambda self: self.env.company)
    cut_id = fields.Many2one('mrp.cut', check_company=True, required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_qty = fields.Float(string="Qty Finished", digits='Product Unit of Measure')
    product_price = fields.Float(string="Price Unit")
    product_total = fields.Float(string="Product Total", digits='Product Unit of Measure',
                                 compute="_compute_product_total")
    type_product_finished = fields.Selection([('product', 'Product'), ('residual', 'Residual'), ('merma', 'Merma')],
                                             string="Type of Product Finished", related='product_id.type_product_finished')
    check_cost_static = fields.Boolean(string="¿Static Cost in Cutting?", default=False)
    product_percent = fields.Float(string="Product Percent", digits='Product Unit of Measure',
                                     compute="_compute_product_percent")

    @api.depends('product_qty')
    def _compute_product_total(self):
        for rec in self:
            rec.product_total = rec.product_price * rec.product_qty

    @api.depends('product_qty')
    def _compute_product_percent(self):
        for rec in self:
            if rec.product_qty > 0 and rec.cut_id.product_qty > 0:
                print(rec.cut_id.product_qty)
                rec.product_percent = rec.product_qty * 100 / rec.cut_id.product_qty
            else:
                rec.product_percent = 0.0