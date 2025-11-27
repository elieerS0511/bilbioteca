from odoo import models, fields, api

class Libro(models.Model):
    _name = 'biblioteca.libro'
    _description = 'Libro'

    name = fields.Char(string='Título', required=True)
    autor_id = fields.Many2one('biblioteca.autor', string='Autor', required=True)
    editorial = fields.Char(string='Editorial')
    anio_publicacion = fields.Integer(string='Año de Publicación')

    multa = fields.Float(string='Multa por Atraso', default=0.0)
    monto = fields.Float(string='Monto por Prestamo', default=0.0)

    genero = fields.Selection([
        ('ficcion', 'Ficción'),
        ('ciencia', 'Ciencia'),
        ('historia', 'Historia'),
        ('biografia', 'Biografía'),
        ('infantil', 'Infantil'),
        ('otros', 'Otros'),
    ], string='Género', default='ficcion')
    
    estado = fields.Selection([
        ('disponible', 'Disponible'),
        ('prestado', 'Prestado'),
        ('atrasado', 'Atrasado'),
    ], string='Estado', default='disponible')
    
    descripcion = fields.Text(string='Descripción')
    active = fields.Boolean(string='Activo', default=True)
    
    prestamo_ids = fields.One2many('biblioteca.prestamo', 'libro_id', string='Préstamos')

class Autor(models.Model):
    _name = 'biblioteca.autor'
    _description = 'Autor'

    name = fields.Char(string='Nombre', required=True)
    nacionalidad = fields.Char(string='Nacionalidad')
    fecha_nacimiento = fields.Date(string='Fecha de Nacimiento')
    biografia = fields.Text(string='Biografía')
    active = fields.Boolean(string='Activo', default=True)
    
    libro_ids = fields.One2many('biblioteca.libro', 'autor_id', string='Libros')
    
    total_libros = fields.Integer(string='Total de Libros', compute='_compute_total_libros')
    
    @api.depends('libro_ids')
    def _compute_total_libros(self):
        for autor in self:
            autor.total_libros = len(autor.libro_ids)

class Miembro(models.Model):
    _name = 'biblioteca.miembro'
    _description = 'Miembro de la Biblioteca'

    name = fields.Char(string='Nombre Completo', required=True)
    codigo_miembro = fields.Char(string='Código', default='Nuevo', readonly=True)
    
    dni = fields.Char(string='DNI / Documento', required=True)
    email = fields.Char(string='Email')
    telefono = fields.Char(string='Teléfono')
    direccion = fields.Char(string='Dirección')

    fecha_registro = fields.Date(default=fields.Date.today)
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('suspendido', 'Suspendido'),
        ('bloqueado', 'Bloqueado'),
        ('inactivo', 'Inactivo')
    ], default='activo')

    # Control de préstamos y multas
    prestamo_ids = fields.One2many('biblioteca.prestamo', 'miembro_id', string='Préstamos')
    prestamos_activos = fields.Integer(compute='_compute_prestamos_activos')
    deuda_total = fields.Float(compute='_compute_deuda_total')

    @api.depends('prestamo_ids.estado')
    def _compute_prestamos_activos(self):
        for m in self:
            m.prestamos_activos = len(m.prestamo_ids.filtered(lambda p: p.estado == 'prestado'))


    @api.depends('prestamo_ids.multa')
    def _compute_deuda_total(self):
        for m in self:
            multas = m.prestamo_ids.mapped('multa')
            m.deuda_total = sum(multas)


