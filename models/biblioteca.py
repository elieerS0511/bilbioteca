from odoo import models, fields, api

class Libro(models.Model):
    """
    Clase que representa un libro dentro del sistema de la biblioteca.
    Cada registro de este modelo es un libro único con sus atributos.
    """
    _name = 'biblioteca.libro'
    _description = 'Libro de la Biblioteca'

    # ==================== CAMPOS DEL LIBRO ====================
    name = fields.Char(string='Título', required=True, help="Título principal del libro.")
    autor_id = fields.Many2one('biblioteca.autor', string='Autor', required=True, help="Autor del libro.")
    editorial = fields.Char(string='Editorial', help="Editorial que publicó el libro.")
    anio_publicacion = fields.Integer(string='Año de Publicación', help="Año en que el libro fue publicado.")

    multa = fields.Float(string='Multa por Atraso', default=0.0, help="Costo de la multa por cada día de atraso en la devolución.")
    monto = fields.Float(string='Monto por Prestamo', default=0.0, help="Costo base para prestar el libro.")

    genero = fields.Selection([
        ('ficcion', 'Ficción'),
        ('ciencia', 'Ciencia'),
        ('historia', 'Historia'),
        ('biografia', 'Biografía'),
        ('infantil', 'Infantil'),
        ('otros', 'Otros'),
    ], string='Género', default='ficcion', help="Género literario al que pertenece el libro.")

    estado = fields.Selection([
        ('disponible', 'Disponible'),
        ('prestado', 'Prestado'),
        ('atrasado', 'Atrasado'),
    ], string='Estado', default='disponible', help="Estado actual del libro en la biblioteca.")

    descripcion = fields.Text(string='Descripción', help="Sinopsis o resumen del contenido del libro.")
    active = fields.Boolean(string='Activo', default=True, help="Indica si el registro está activo o archivado (borrado lógico).")

    prestamo_ids = fields.One2many('biblioteca.prestamo', 'libro_id', string='Préstamos', help="Historial de todos los préstamos de este libro.")

class Autor(models.Model):
    """
    Clase que representa a un autor de libros.
    Almacena información biográfica y la relación con los libros que ha escrito.
    """
    _name = 'biblioteca.autor'
    _description = 'Autor de Libros'

    # ==================== CAMPOS DEL AUTOR ====================
    name = fields.Char(string='Nombre', required=True, help="Nombre completo del autor.")
    nacionalidad = fields.Char(string='Nacionalidad', help="País de origen del autor.")
    fecha_nacimiento = fields.Date(string='Fecha de Nacimiento', help="Fecha de nacimiento del autor.")
    biografia = fields.Text(string='Biografía', help="Resumen de la vida y obra del autor.")
    active = fields.Boolean(string='Activo', default=True, help="Indica si el autor está activo en el sistema.")

    # Campo relacional que muestra todos los libros escritos por este autor.
    libro_ids = fields.One2many('biblioteca.libro', 'autor_id', string='Libros')

    # Campo calculado que cuenta el total de libros asociados a este autor.
    total_libros = fields.Integer(string='Total de Libros', compute='_compute_total_libros', store=True, help="Número total de libros de este autor en la biblioteca.")

    @api.depends('libro_ids')
    def _compute_total_libros(self):
        """
        Calcula el número total de libros asociados a cada autor.
        Este método se dispara automáticamente cuando el campo `libro_ids` cambia.
        El resultado se almacena en la base de datos gracias a `store=True`.
        """
        for autor in self:
            autor.total_libros = len(autor.libro_ids)

class Miembro(models.Model):
    """
    Clase que representa a un miembro registrado en la biblioteca.
    Contiene la información personal del miembro y su historial de préstamos.
    """
    _name = 'biblioteca.miembro'
    _description = 'Miembro de la Biblioteca'

    # ==================== CAMPOS DEL MIEMBRO ====================
    name = fields.Char(string='Nombre Completo', required=True, help="Nombre y apellidos del miembro.")
    codigo_miembro = fields.Char(string='Código', default='Nuevo', readonly=True, help="Código único de identificación para el miembro.")

    dni = fields.Char(string='DNI / Documento', required=True, help="Documento Nacional de Identidad o equivalente.")
    email = fields.Char(string='Email', help="Correo electrónico del miembro.")
    telefono = fields.Char(string='Teléfono', help="Número de contacto del miembro.")
    direccion = fields.Char(string='Dirección', help="Dirección de residencia del miembro.")

    fecha_registro = fields.Date(string='Fecha de Registro', default=fields.Date.today, readonly=True, help="Fecha en que el miembro se unió a la biblioteca.")
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('suspendido', 'Suspendido'),
        ('bloqueado', 'Bloqueado'),
        ('inactivo', 'Inactivo')
    ], string='Estado de Membresía', default='activo', help="Estado actual de la membresía del miembro.")

    # ==================== CAMPOS RELACIONALES Y CALCULADOS ====================
    # Historial de todos los préstamos realizados por este miembro.
    prestamo_ids = fields.One2many('biblioteca.prestamo', 'miembro_id', string='Préstamos')

    # Campo calculado para contar los préstamos que aún no han sido devueltos.
    prestamos_activos = fields.Integer(string='Préstamos Activos', compute='_compute_prestamos_activos', help="Número de libros que el miembro tiene prestados actualmente.")

    # Campo calculado para sumar todas las multas pendientes de pago.
    deuda_total = fields.Float(string='Deuda Total', compute='_compute_deuda_total', help="Suma total de las multas acumuladas por préstamos atrasados.")

    @api.depends('prestamo_ids.estado')
    def _compute_prestamos_activos(self):
        """
        Calcula el número de préstamos que están en estado 'prestado'.
        Se actualiza cada vez que cambia el estado de alguno de los préstamos del miembro.
        """
        for m in self:
            # Filtra los préstamos para contar solo aquellos cuyo estado es 'prestado'.
            m.prestamos_activos = len(m.prestamo_ids.filtered(lambda p: p.estado == 'prestado'))

    @api.depends('prestamo_ids.multa')
    def _compute_deuda_total(self):
        """
        Calcula la deuda total del miembro sumando las multas de todos sus préstamos.
        Se actualiza si el campo 'multa' de alguno de sus préstamos cambia.
        """
        for m in self:
            # Extrae el valor de la multa de cada préstamo y los suma.
            multas = m.prestamo_ids.mapped('multa')
            m.deuda_total = sum(multas)
