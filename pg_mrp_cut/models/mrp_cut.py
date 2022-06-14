import datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from ast import literal_eval
from odoo.tools.float_utils import float_round, float_repr


class MrpCut(models.Model):
    _name = 'mrp.cut'
    _description = 'Cutting Order'
    _date_name = 'date_planned_start'
    _order = 'date_planned_start desc,id'

    @api.model
    def _get_default_date_planned_start(self):
        if self.env.context.get('default_date_deadline'):
            return fields.Datetime.to_datetime(self.env.context.get('default_date_deadline'))
        return datetime.datetime.now()

    @api.model
    def _get_default_picking_type(self):
        company_id = self.env.context.get('default_company_id', self.env.company.id)
        return self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_cutting')
        ], limit=1).id

    name = fields.Char('Reference', copy=False, readonly=True, default=lambda x: _('New'))

    product_id = fields.Many2one('product.product', 'Product',
                                 domain="[('bom_ids', '!=', False), ('bom_ids.active', '=', True), "
                                        "('bom_ids.type', '=', 'cutting'), "
                                        "('type', 'in', ['product']), '|', ('company_id', '=', False), "
                                        "('company_id', '=', company_id)]",
                                 readonly=True, required=True, check_company=True,
                                 states={'draft': [('readonly', False)]})


    product_qty = fields.Float(
        'Quantity to process',
        default=1.0, digits='Product Unit of Measure',
        readonly=True, required=True, tracking=True,
        states={'draft': [('readonly', False)], 'confirmed': [('readonly', False)]})

    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        readonly=True, required=True,
        states={'draft': [('readonly', False)]})
    product_cost = fields.Float(related="product_id.standard_price", readonly=True)
    product_cost_total = fields.Float(string="Product Cost total", readonly=True, compute="_compute_cost_total")
    date_planned_start = fields.Datetime(
        'Scheduled Date', copy=False, default=_get_default_date_planned_start,
        help="Date at which you plan to start the operation.",
        index=True, required=True)

    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        readonly=True, states={'draft': [('readonly', False)]},
        domain="""[
                '&',
                    '|',
                        ('company_id', '=', False),
                        ('company_id', '=', company_id),
                    '&',
                        '|',
                            ('product_id','=',product_id),
                            '&',
                                ('product_tmpl_id.product_variant_ids','=',product_id),
                                ('product_id','=',False),
                ('type', '=', 'cutting')]""",
        check_company=True, copy=False,
        help="Bill of Materials allow you to define the list of required components to make a finished product.")

    move_raw_ids = fields.One2many('mrp.cut.line', 'cut_id', 'Results', copy=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, index=True,
                                 required=True)

    location_src_id = fields.Many2one(
        'stock.location', 'Source Location',
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        required=True, states={'done': [('readonly', True)]})

    location_dest_id = fields.Many2one(
        'stock.location', 'Source Location',
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        required=True, states={'done': [('readonly', True)]})

    # required picking_type_id
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type',
        domain="[('code', '=', 'mrp_cutting'), ('company_id', '=', company_id)]",
        default=_get_default_picking_type, check_company=True)

    product_src_stock_qty = fields.Char(string="Qty Available in Stock", compute="calculate_value_stock_qty")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('to_close', 'Closed'),
        ('cancel', 'Cancelled')], string='State', default='draft', copy=False, index=True, readonly=True)

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('mrp.cut') or _('New')
        cutting = super(MrpCut, self).create(values)
        return cutting

    @api.depends('product_qty', 'product_cost')
    def _compute_cost_total(self):
        for rec in self:
            rec.product_cost_total = rec.product_qty * rec.product_cost

    @api.depends('location_src_id')
    def calculate_value_stock_qty(self):
        for rec in self:
            product_unit = self.env['decimal.precision'].sudo().search([('name', '=', 'Product Unit of Measure')],
                                                                       limit=1)
            if rec.location_src_id and rec.product_id:
                stocks = self.env['stock.quant'].search(
                    [('product_id', '=', rec.product_id.id), ('location_id', '=', rec.location_src_id.id)])
                if stocks:
                    total_stock = 0
                    for stock in stocks:
                        total_stock += stock.quantity
                    if total_stock > 0:
                        total = float_round(total_stock, precision_digits=product_unit.digits or 2)
                        rec.product_src_stock_qty = total
                    else:
                        rec.product_src_stock_qty = "0"
                else:
                    rec.product_src_stock_qty = "0"
            else:
                rec.product_src_stock_qty = "0"

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        return True

    def create_out_product_cutting(self, rec,picking_type):
        stock_picking = self.env['stock.picking']
        location_dest_id = self.env['stock.location'].search([('usage', '=', 'cutting')], limit=1)
        stock_less = stock_picking.create({
            'picking_type_id': picking_type.id,
            'location_id': rec.location_src_id.id,
            'location_dest_id': location_dest_id.id,
            'company_id': 1,
            'partner_id': 3,
            'move_ids_without_package': [(0, 0, {
                'name': rec.product_id.name,
                'product_id': rec.product_id.id,
                'product_uom': rec.product_uom_id.id,
                'price_unit': rec.product_cost,
                'product_uom_qty': rec.product_qty,
                'quantity_done': rec.product_qty,
                'location_id': rec.location_src_id.id,
                'location_dest_id': location_dest_id.id,
                'mrp_cut_id': rec.id,
            })]
        })
        stock_less.action_confirm()
        stock_less.button_validate()

    def create_int_products_cutting(self, rec, lines, picking_type):

        stock_picking = self.env['stock.picking']
        location_dest_id = self.env['stock.location'].search([('usage', '=', 'cutting')], limit=1)
        stock_less = stock_picking.create({
            'picking_type_id': picking_type.id,
            'location_id': location_dest_id.id,
            'location_dest_id': rec.location_src_id.id,
            'company_id': 1,
            'partner_id': 3,
            'move_ids_without_package': [(0, 0, {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'price_unit': line.product_price,
                'product_uom': line.product_id.uom_id.id,
                'product_uom_qty': line.product_qty,
                'quantity_done': line.product_qty,
                'location_id': location_dest_id.id,
                'location_dest_id': rec.location_src_id.id,
                'mrp_cut_id': rec.id,
            }) for line in lines.filtered(lambda l: l.product_price > 0)]
        })
        stock_less.action_confirm()
        stock_less.button_validate()

    def check_restrictions_cutting_process(self, total_cost, record):
        if total_cost != record.product_cost_total:
            raise UserError(
                _('Cost in lines is not equal to the total cost from cutting product'))
        elif record.product_qty > float(record.product_src_stock_qty):
            raise UserError(
                _('Stock available for cutting product is %s and stock that you want process is %s, no stock enough.')
                % (record.product_src_stock_qty, record.product_qty))
        return True

    def button_mark_done(self):
        for rec in self:
            cost_remaining = 0
            qty_remaining = 0
            cost_actuallly = 0
            qty_actuallly = 0
            qty_done = 0
            for line in rec.move_raw_ids:
                qty_done = qty_done + line.product_qty

            if qty_done != rec.product_qty:
                raise UserError(
                    _('Qty in order is not same that was consumed'))

            for line in rec.move_raw_ids:
                if line.product_price != 0 or line.product_id.type_product_finished == 'merma':
                    cost_actuallly = cost_actuallly + line.product_total
                    qty_actuallly = qty_actuallly + line.product_qty
            cost_remaining = rec.product_cost_total - cost_actuallly
            qty_remaining = rec.product_qty - qty_actuallly
            if qty_remaining > 0:
                for line in rec.move_raw_ids:
                    if line.check_cost_static is False and line.product_id.type_product_finished == 'product':
                        line.product_price = cost_remaining / qty_remaining
                        line.product_total = line.product_price * line.product_qty
            cost_actualllys = 0
            for line in rec.move_raw_ids:
                cost_actualllys = cost_actualllys + line.product_total

            # Check restriction before processing cutting

            self.check_restrictions_cutting_process(total_cost=float_round(cost_actualllys,2), record=rec)

            # create stock moves for insumes
            self.create_out_product_cutting(rec=rec, picking_type=rec.picking_type_id)
            self.create_int_products_cutting(rec, lines=rec.move_raw_ids,picking_type=rec.picking_type_id)

            rec.state = 'done'

    @api.onchange('product_id', 'company_id')
    def onchange_product_id(self):
        """ Finds UoM of changed product. """
        if self.product_id != self._origin.product_id:
            self.location_src_id = False
        if not self.product_id:
            self.bom_id = False
        else:
            bom = self.env['mrp.bom']._bom_find(product=self.product_id, company_id=self.company_id.id,
                                                bom_type='cutting')
            if bom:
                self.bom_id = bom.id
                self.product_qty = self.bom_id.product_qty
                self.product_uom_id = self.bom_id.product_uom_id.id
                if self.product_qty > 0:
                    self.product_cost = self.product_id.standard_price
                    self.product_cost_total = self.product_id.standard_price * self.product_qty
            else:
                self.bom_id = False
                self.product_uom_id = self.product_id.uom_id.id

            return {'domain': {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        self.product_qty = self.bom_id.product_qty
        self.product_uom_id = self.bom_id.product_uom_id.id
        self.move_raw_ids = [(2, line.id) for line in self.move_raw_ids.filtered(lambda m: m.product_id)]

    @api.onchange('bom_id', 'product_id', 'product_qty', 'product_uom_id')
    def _onchange_despiece_lines(self):
        # Clear move raws if we are changing the product. In case of creation (self._origin is empty),
        # we need to avoid keeping incorrect lines, so clearing is necessary too.
        if self.product_id != self._origin.product_id:
            self.move_raw_ids = [(5,)]
        if self.bom_id and self.product_qty > 0:
            # keep manual entries
            self.move_raw_ids = [(5,)]
            bom_values = self.bom_id.bom_line_ids
            lista_lines = []
            for bom_lines in bom_values:
                # add new entries
                product_price = 0
                if bom_lines.check_cost_static is True:
                    product_price = bom_lines.product_id.standard_price
                lista_lines.append((0, 0, {
                    'product_id': bom_lines.product_id.id,
                    'type_product_finished': bom_lines.type_product_finished,
                    'check_cost_static': bom_lines.check_cost_static,
                    'product_price': product_price,
                    'company_id': bom_lines.company_id.id
                }))

            self.move_raw_ids = lista_lines
        else:
            self.move_raw_ids = [(5,)]

    def action_view_stock_valuation_layers(self):
        self.ensure_one()
        stock_move = self.env['stock.move'].search([('mrp_cut_id','=', self.id)])
        domain = [('id', 'in', stock_move.stock_valuation_layer_ids.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
        context = literal_eval(action['context'])
        context.update(self.env.context)
        context['no_at_date'] = True
        context['search_default_group_by_product_id'] = False
        return dict(action, domain=domain, context=context)