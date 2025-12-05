from odoo import models, fields, api

class Libro(models.Model):
    """Modelo que representa un libro en la biblioteca."""
    _name = 'biblioteca.libro'
    _description = 'Libro'

    # ==================== CAMPOS DEL LIBRO ====================
    name = fields.Char(string='Título', required=True)
    autor_id = fields.Many2one('biblioteca.autor', string='Autor', required=True)
    editorial = fields.Char(string='Editorial')
    anio_publicacion = fields.Integer(string='Año de Publicación')

    multa = fields.Float(string='Multa por Atraso', default=0.0)  # Multa por día de atraso
    monto = fields.Float(string='Monto por Prestamo', default=0.0)  # Precio por prestar el libro

    genero = fields.Selection([  # Categorización del libro
        ('ficcion', 'Ficción'),
        ('ciencia', 'Ciencia'),
        ('historia', 'Historia'),
        ('biografia', 'Biografía'),
        ('infantil', 'Infantil'),
        ('otros', 'Otros'),
    ], string='Género', default='ficcion')
    
    estado = fields.Selection([  # Estado actual del libro
        ('disponible', 'Disponible'),
        ('prestado', 'Prestado'),
        ('atrasado', 'Atrasado'),
    ], string='Estado', default='disponible')
    
    descripcion = fields.Text(string='Descripción')
    active = fields.Boolean(string='Activo', default=True)  # Para borrado lógico
    
    prestamo_ids = fields.One2many('biblioteca.prestamo', 'libro_id', string='Préstamos')  # Historial de préstamos

class Autor(models.Model):
    """Modelo que representa un autor de libros."""
    _name = 'biblioteca.autor'
    _description = 'Autor'

    # ==================== CAMPOS DEL AUTOR ====================
    name = fields.Char(string='Nombre', required=True)
    nacionalidad = fields.Char(string='Nacionalidad')
    fecha_nacimiento = fields.Date(string='Fecha de Nacimiento')
    biografia = fields.Text(string='Biografía')
    active = fields.Boolean(string='Activo', default=True)
    
    libro_ids = fields.One2many('biblioteca.libro', 'autor_id', string='Libros')  # Libros escritos por este autor
    
    total_libros = fields.Integer(string='Total de Libros', compute='_compute_total_libros')  # Campo calculado
    
    @api.depends('libro_ids')
    def _compute_total_libros(self):
        """Calcula el número total de libros escritos por el autor."""
        for autor in self:
            autor.total_libros = len(autor.libro_ids)

class Miembro(models.Model):
    """Modelo que representa un miembro de la biblioteca."""
    _name = 'biblioteca.miembro'
    _description = 'Miembro de la Biblioteca'

    # ==================== CAMPOS DEL MIEMBRO ====================
    name = fields.Char(string='Nombre Completo', required=True)
    codigo_miembro = fields.Char(string='Código', default='Nuevo', readonly=True)  # Código único del miembro
    
    dni = fields.Char(string='DNI / Documento', required=True)
    email = fields.Char(string='Email')
    telefono = fields.Char(string='Teléfono')
    direccion = fields.Char(string='Dirección')

    fecha_registro = fields.Date(default=fields.Date.today)
    estado = fields.Selection([  # Estado de la membresía
        ('activo', 'Activo'),
        ('suspendido', 'Suspendido'),
        ('bloqueado', 'Bloqueado'),
        ('inactivo', 'Inactivo')
    ], default='activo')

    # ==================== CAMPOS RELACIONALES Y CALCULADOS ====================
    prestamo_ids = fields.One2many('biblioteca.prestamo', 'miembro_id', string='Préstamos')  # Historial de préstamos
    prestamos_activos = fields.Integer(compute='_compute_prestamos_activos')  # Préstamos no devueltos
    deuda_total = fields.Float(compute='_compute_deuda_total')  # Suma de multas pendientes

    @api.depends('prestamo_ids.estado')
    def _compute_prestamos_activos(self):
        """Calcula cuántos préstamos activos (no devueltos) tiene el miembro."""
        for m in self:
            m.prestamos_activos = len(m.prestamo_ids.filtered(lambda p: p.estado == 'prestado'))

    @api.depends('prestamo_ids.multa')
    def _compute_deuda_total(self):
        """Calcula la deuda total del miembro sumando todas sus multas."""
        for m in self:
            multas = m.prestamo_ids.mapped('multa')
            m.deuda_total = sum(multas)