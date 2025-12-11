from odoo import models, fields, api
from datetime import timedelta

class Prestamo(models.Model):
    """
    Clase que representa el préstamo de un libro a un miembro de la biblioteca.
    Este modelo gestiona todo el ciclo de vida de un préstamo, desde su creación
    hasta la devolución del libro y el cálculo de posibles multas.
    """
    _name = 'biblioteca.prestamo'
    _description = 'Préstamo de Libro'
    _order = 'fecha_prestamo desc'  # Ordena los registros por fecha de préstamo, del más reciente al más antiguo.

    # ==================== CAMPOS DEL MODELO ====================
    name = fields.Char(string='Referencia', default='Nuevo', readonly=True, help="Identificador único y secuencial del préstamo.")
    libro_id = fields.Many2one('biblioteca.libro', string='Libro', required=True, help="Libro que se está prestando.")
    miembro_id = fields.Many2one('biblioteca.miembro', string='Miembro', required=True, help="Miembro que solicita el préstamo.")

    email = fields.Char(string='Email', readonly=True, help="Email del miembro (se copia automáticamente).")
    telefono = fields.Char(string='Teléfono', readonly=True, help="Teléfono del miembro (se copia automáticamente).")

    fecha_prestamo = fields.Datetime(string='Fecha de Préstamo', default=fields.Datetime.now, required=True, help="Fecha y hora en que se realiza el préstamo.")
    fecha_devolucion = fields.Datetime(string='Fecha Devolución', compute='_compute_fecha_devolucion', store=True, readonly=True, help="Fecha límite para devolver el libro sin incurrir en multas.")

    estado = fields.Selection([
        ('prestado', 'Prestado'),
        ('devuelto', 'Devuelto'),
        ('atrasado', 'Atrasado'),
    ], string='Estado', default='prestado', help="Estado actual del préstamo.")

    dias_prestamo = fields.Integer(string='Días de Préstamo', default=15, help="Número de días acordados para el préstamo.")

    monto = fields.Float(string='Monto del Préstamo', readonly=True, help="Costo del préstamo (se copia desde el libro).")
    multa = fields.Float(string='Multa Total', readonly=True, help="Multa total acumulada por días de atraso.")

    # ==================== MÉTODOS DE CÁLCULO ====================
    @api.depends('fecha_prestamo', 'dias_prestamo')
    def _compute_fecha_devolucion(self):
        """
        Calcula la fecha de devolución basándose en la fecha de préstamo y los días de duración.
        Este método se activa cuando 'fecha_prestamo' o 'dias_prestamo' cambian.
        El resultado se guarda en la base de datos (`store=True`).
        """
        for prestamo in self:
            if prestamo.fecha_prestamo:
                prestamo.fecha_devolucion = prestamo.fecha_prestamo + timedelta(days=prestamo.dias_prestamo)

    # ==================== MÉTODOS ONCHANGE ====================
    @api.onchange('miembro_id')
    def _onchange_miembro_id(self):
        """
        Cuando se selecciona un miembro en el formulario, este método copia
        automáticamente su email y teléfono a los campos correspondientes del préstamo.
        """
        if self.miembro_id:
            self.email = self.miembro_id.email
            self.telefono = self.miembro_id.telefono

    @api.onchange('libro_id')
    def _onchange_libro_id(self):
        """
        Cuando se selecciona un libro, este método copia el costo del préstamo
        desde la ficha del libro y se asegura de que la multa inicial sea cero.
        """
        if self.libro_id:
            self.monto = self.libro_id.monto
            self.multa = 0.0

    # ==================== MÉTODOS CRUD (Create, Read, Update, Delete) ====================
    @api.model
    def create(self, vals):
        """
        Se sobrescribe el método 'create' para añadir lógica de negocio adicional:
        1. Asigna un número de secuencia único ('name') al nuevo préstamo.
        2. Copia el `monto` desde el libro para asegurar consistencia.
        3. Actualiza el estado del libro a 'prestado'.
        """
        # Genera una secuencia única si no se proporciona una.
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('biblioteca.prestamo.sequence') or 'Nuevo'

        # Si se está creando un préstamo para un libro, copia su monto.
        # Esto es crucial para creaciones programáticas donde el `onchange` no se dispara.
        if vals.get('libro_id'):
            libro = self.env['biblioteca.libro'].browse(vals['libro_id'])
            vals['monto'] = libro.monto

        # Llama al método 'create' original para crear el registro en la base de datos.
        prestamo = super(Prestamo, self).create(vals)

        # Cambia el estado del libro a 'prestado'.
        if prestamo.libro_id:
            prestamo.libro_id.estado = 'prestado'

        return prestamo

    # ==================== MÉTODOS DE ACCIÓN (Botones) ====================
    def action_entregado(self):
        """
        Acción principal para procesar la devolución de un libro.
        Esta es la lógica que se ejecuta al presionar el botón 'Marcar como Entregado'.
        - Verifica si el libro se devuelve con retraso.
        - Si hay retraso, cambia el estado a 'Atrasado' y calcula la multa.
        - Si se devuelve a tiempo, cambia el estado a 'Devuelto'.
        - En cualquier caso, el libro vuelve a estar 'Disponible'.
        """
        for prestamo in self:
            # Comprobar si la fecha de devolución está definida para evitar errores
            if not prestamo.fecha_devolucion:
                prestamo.estado = 'devuelto'
                if prestamo.libro_id:
                    prestamo.libro_id.estado = 'disponible'
                continue

            hoy = fields.Datetime.now()
            if hoy > prestamo.fecha_devolucion:
                prestamo.estado = 'atrasado'
                prestamo.action_calcular_multa()  # Calcula la multa correspondiente
            else:
                prestamo.estado = 'devuelto'
                prestamo.multa = 0.0

            # Marcar el libro como disponible
            if prestamo.libro_id:
                prestamo.libro_id.estado = 'disponible'

    def action_calcular_multa(self):
        """
        Calcula la multa por días de atraso usando la multa por día del libro.
        Esta acción puede ser llamada desde el botón 'Calcular Multa' o internamente.
        """
        for prestamo in self:
            if not prestamo.fecha_devolucion:
                prestamo.multa = 0.0
                continue

            hoy = fields.Datetime.now()
            if hoy > prestamo.fecha_devolucion:
                dias_atraso = (hoy - prestamo.fecha_devolucion).days
                multa_dia = prestamo.libro_id.multa or 0.0
                prestamo.multa = dias_atraso * multa_dia
                # Asegura que el estado del préstamo sea consistente con la existencia de una multa.
                if prestamo.multa > 0:
                    prestamo.estado = 'atrasado'
            else:
                prestamo.multa = 0.0
