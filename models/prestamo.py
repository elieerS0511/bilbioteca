from odoo import models, fields, api
from datetime import timedelta

class Prestamo(models.Model):
    """Modelo que representa un préstamo de libro en la biblioteca."""
    _name = 'biblioteca.prestamo'
    _description = 'Préstamo de Libro'
    _order = 'fecha_prestamo desc'  # Ordena por fecha de préstamo descendente

    # ==================== CAMPOS DEL MODELO ====================
    name = fields.Char(string='Referencia', default='Nuevo', readonly=True)  # Número único del préstamo
    libro_id = fields.Many2one('biblioteca.libro', string='Libro', required=True)  # Libro prestado
    miembro_id = fields.Many2one('biblioteca.miembro', string='Miembro', required=True)  # Miembro que pide prestado

    email = fields.Char(string='Email')  # Email del miembro (copiado automáticamente)
    telefono = fields.Char(string='Teléfono')  # Teléfono del miembro (copiado automáticamente)

    fecha_prestamo = fields.Datetime(string='Fecha de Préstamo', default=fields.Datetime.now, required=True)
    fecha_devolucion = fields.Datetime(string='Fecha Devolución', compute='_compute_fecha_devolucion', store=True)

    estado = fields.Selection([
        ('prestado', 'Prestado'),
        ('devuelto', 'Devuelto'),
        ('atrasado', 'Atrasado'),
    ], default='prestado')  # Estado actual del préstamo

    dias_prestamo = fields.Integer(string='Días de Préstamo', default=15)  # Duración del préstamo

    monto = fields.Float(string='Monto del Préstamo', default=0.0)  # Precio por prestar el libro
    multa = fields.Float(string='Multa Total', default=0.0)  # Multa acumulada por atraso

    # ==================== MÉTODOS DE CÁLCULO ====================
    @api.depends('fecha_prestamo', 'dias_prestamo')
    def _compute_fecha_devolucion(self):
        """Calcula automáticamente la fecha de devolución sumando días de préstamo a la fecha inicial."""
        for prestamo in self:
            if prestamo.fecha_prestamo:
                prestamo.fecha_devolucion = prestamo.fecha_prestamo + timedelta(days=prestamo.dias_prestamo)

    # ==================== MÉTODOS ONCHANGE ====================
    @api.onchange('miembro_id')
    def _onchange_miembro_id(self):
        """Copia automáticamente el email y teléfono del miembro seleccionado."""
        for prestamo in self:
            if prestamo.miembro_id:
                prestamo.email = prestamo.miembro_id.email
                prestamo.telefono = prestamo.miembro_id.telefono

    @api.onchange('libro_id')
    def _onchange_libro_id(self):
        """Copia el monto del préstamo del libro seleccionado y resetea la multa."""
        for prestamo in self:
            if prestamo.libro_id:
                prestamo.monto = prestamo.libro_id.monto
                # La multa total se calculará solo si hay atraso
                prestamo.multa = 0.0

    # ==================== MÉTODOS CRUD ====================
    @api.model
    def create(self, vals):
        """Sobrescribe el método create para:
           1. Generar una referencia única automática
           2. Copiar el monto del libro
           3. Cambiar el estado del libro a 'prestado'
        """
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

    # ==================== MÉTODOS DE ACCIÓN ====================
    def action_devolver_libro(self):
        """Marca un libro como devuelto y verifica si hay atraso."""
        for prestamo in self:
            hoy = fields.Datetime.now()

            if hoy > prestamo.fecha_devolucion:
                prestamo.estado = 'atrasado'
                prestamo.libro_id.estado = 'atrasado'
            else:
                prestamo.estado = 'prestado'
                prestamo.libro_id.estado = 'prestado'

    def action_calcular_multa(self):
        """Calcula la multa por días de atraso usando la multa por día del libro."""
        for prestamo in self:
            if not prestamo.fecha_devolucion:
                continue

            hoy = fields.Datetime.now()

            if hoy > prestamo.fecha_devolucion:
                dias_atraso = (hoy - prestamo.fecha_devolucion).days
                multa_dia = prestamo.libro_id.multa or 0.0
                prestamo.multa = dias_atraso * multa_dia
                prestamo.estado = 'atrasado'

    def action_entregado(self):
        """Marca el préstamo como devuelto y el libro como disponible."""
        for prestamo in self:
            prestamo.estado = 'devuelto'
            if prestamo.libro_id:
                prestamo.libro_id.estado = 'disponible'