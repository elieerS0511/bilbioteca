from odoo import models, fields, api
from datetime import timedelta

class Prestamo(models.Model):
    _name = 'biblioteca.prestamo'
    _description = 'Préstamo de Libro'
    _order = 'fecha_prestamo desc'

    name = fields.Char(string='Referencia', default='Nuevo', readonly=True)
    libro_id = fields.Many2one('biblioteca.libro', string='Libro', required=True)
    miembro_id = fields.Many2one('biblioteca.miembro', string='Miembro', required=True)

    email = fields.Char(string='Email')
    telefono = fields.Char(string='Teléfono')

    fecha_prestamo = fields.Datetime(string='Fecha de Préstamo', default=fields.Datetime.now, required=True)
    fecha_devolucion = fields.Datetime(string='Fecha Devolución', compute='_compute_fecha_devolucion', store=True)

    estado = fields.Selection([
        ('prestado', 'Prestado'),
        ('devuelto', 'Devuelto'),
        ('atrasado', 'Atrasado'),
    ], default='prestado')

    dias_prestamo = fields.Integer(string='Días de Préstamo', default=15)

    monto = fields.Float(string='Monto del Préstamo', default=0.0)
    multa = fields.Float(string='Multa Total', default=0.0)

    # ------------------------------------------------------
    # FECHA AUTOMÁTICA
    # ------------------------------------------------------
    @api.depends('fecha_prestamo', 'dias_prestamo')
    def _compute_fecha_devolucion(self):
        for prestamo in self:
            if prestamo.fecha_prestamo:
                prestamo.fecha_devolucion = prestamo.fecha_prestamo + timedelta(days=prestamo.dias_prestamo)

    # ------------------------------------------------------
    # COPIAR EMAIL Y TELÉFONO DEL MIEMBRO
    # ------------------------------------------------------
    @api.onchange('miembro_id')
    def _onchange_miembro_id(self):
        for prestamo in self:
            if prestamo.miembro_id:
                prestamo.email = prestamo.miembro_id.email
                prestamo.telefono = prestamo.miembro_id.telefono

    # ------------------------------------------------------
    # COPIAR MONTO Y MULTA POR DÍA DESDE EL LIBRO
    # ------------------------------------------------------
    @api.onchange('libro_id')
    def _onchange_libro_id(self):
        for prestamo in self:
            if prestamo.libro_id:
                prestamo.monto = prestamo.libro_id.monto
                # No es multa total, es la multa por día
                # La multa total se calcula cuando haya atraso
                prestamo.multa = 0.0

    # ------------------------------------------------------
    # SETEAR REFERENCIA Y ESTADO DEL LIBRO
    # ------------------------------------------------------
    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'biblioteca.prestamo.sequence'
            ) or 'Nuevo'

        # Copia monto y multa por día al crear
        if vals.get('libro_id'):
            libro = self.env['biblioteca.libro'].browse(vals['libro_id'])
            vals['monto'] = libro.monto

        prestamo = super().create(vals)

        if prestamo.libro_id:
            prestamo.libro_id.estado = 'prestado'

        return prestamo

    # ------------------------------------------------------
    # MARCAR DEVOLUCIÓN
    # ------------------------------------------------------
    def action_devolver_libro(self):
        for prestamo in self:

            hoy = fields.Datetime.now()

            if hoy > prestamo.fecha_devolucion:
                prestamo.estado = 'atrasado'
                prestamo.libro_id.estado = 'atrasado'
            else:
                prestamo.estado = 'prestado'
                prestamo.libro_id.estado = 'prestado'

    # ------------------------------------------------------
    # CALCULAR MULTA DESDE EL LIBRO (MULTA POR DÍA)
    # ------------------------------------------------------
    def action_calcular_multa(self):
        for prestamo in self:
            if not prestamo.fecha_devolucion:
                continue

            hoy = fields.Datetime.now()

            if hoy > prestamo.fecha_devolucion:

                dias_atraso = (hoy - prestamo.fecha_devolucion).days

                multa_dia = prestamo.libro_id.multa or 0.0

                prestamo.multa = dias_atraso * multa_dia
                prestamo.estado = 'atrasado'

    # ------------------------------------------------------
    # LIBRO DEVUELTO
    # ------------------------------------------------------
    def action_entregado(self):
        for prestamo in self:
            prestamo.estado = 'devuelto'
            if prestamo.libro_id:
                prestamo.libro_id.estado = 'disponible'
