from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    type_product_finished = fields.Selection([('product', 'Product'), ('residual', 'Residual'), ('merma', 'Merma')], string="Type of Product Finished")
    check_cost_static = fields.Boolean(string="¿Static Cost in Cutting?", default=False)
