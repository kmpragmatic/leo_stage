from odoo import fields, models, api, _
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    type = fields.Selection(selection_add=[('cutting', 'Cutting')], ondelete={'cutting': 'cascade'})

    @api.onchange('type')
    def onchange_type_cutting(self):
        if self.type == 'cutting':
            self.bom_line_ids = [(5,)]

class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    type_product_finished = fields.Selection([('product', 'Product'), ('residual', 'Residual'), ('merma', 'Merma')],
                                             string="Type of Product Finished")
    check_cost_static = fields.Boolean(string="¿Static Cost in Cutting?", default=False)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            if self.product_id.product_tmpl_id.type_product_finished:
                self.type_product_finished = self.product_id.product_tmpl_id.type_product_finished
            if self.product_id.product_tmpl_id.check_cost_static:
                self.check_cost_static = self.product_id.product_tmpl_id.check_cost_static
            if self.type_product_finished == 'product' and self.check_cost_static is False:
                previous_product = self.bom_id.bom_line_ids.filtered(lambda d: d.type_product_finished == 'product'
                                                                               and d.check_cost_static is False
                                                                               and d.bom_id.type == 'cutting')
                if len(previous_product) > 1:
                    raise UserError(
                        _("A product with type of product finished is 'Product' and Static Cost is not Check, "
                          "only can exist inside material list one product with this characteristics."))

