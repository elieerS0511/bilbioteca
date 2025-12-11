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
        2. Actualiza el estado del libro a 'prestado' para que no pueda ser prestado por otra persona.
        """
        # Genera una secuencia única si no se proporciona una.
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('biblioteca.prestamo.sequence') or 'Nuevo'

        # Llama al método 'create' original para crear el registro en la base de datos.
        prestamo = super().create(vals)

        # Cambia el estado del libro a 'prestado'.
        if prestamo.libro_id:
            prestamo.libro_id.estado = 'prestado'

        return prestamo

    # ==================== MÉTODOS DE ACCIÓN (Botones) ====================
    def action_devolver_libro(self):
        """
        Acción ejecutada al intentar devolver un libro.
        Verifica si la devolución se realiza fuera de plazo para cambiar el estado a 'atrasado'.
        Si se devuelve a tiempo, el estado del libro vuelve a 'disponible'.
        """
        self.ensure_one()
        hoy = fields.Datetime.now()

        if hoy > self.fecha_devolucion:
            self.estado = 'atrasado'
            self.libro_id.estado = 'disponible' # Aunque esté atrasado, ya está disponible
            self.action_calcular_multa() # Calcula la multa correspondiente.
        else:
            self.estado = 'devuelto'
            self.libro_id.estado = 'disponible'

    def action_calcular_multa(self):
        """
        Calcula la multa basándose en los días de atraso y el costo de multa diario del libro.
        Esta acción puede ser llamada manualmente o por otros métodos.
        """
        self.ensure_one()
        if self.fecha_devolucion and fields.Datetime.now() > self.fecha_devolucion:
            dias_atraso = (fields.Datetime.now() - self.fecha_devolucion).days
            multa_dia = self.libro_id.multa or 0.0
            self.multa = dias_atraso * multa_dia

    def action_entregado(self):
        """
        Acción final que marca el préstamo como 'devuelto' y el libro como 'disponible'.
        Es el paso final del proceso de devolución.
        """
        self.ensure_one()
        self.estado = 'devuelto'
        if self.libro_id:
            self.libro_id.estado = 'disponible'
