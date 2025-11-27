{
    'name': 'Sistema de Gestión de Biblioteca',
    'version': '18.0.0.1',
    'summary': 'Módulo para gestionar libros, autores y préstamos en una biblioteca',
    'description': """
        Sistema completo de gestión bibliotecaria
        =========================================
        * Gestión de libros y autores
        * Control de préstamos
        * Catálogo digital
        * Reportes de préstamos
    """,
    'author': 'ESGD NYVC',
    'website': 'https://www.Example.com',
    'category': '',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/biblioteca_data.xml',
        'views/biblioteca_views.xml',
        'views/prestamo_views.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}