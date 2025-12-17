# sales/advanced_pdf_exporter.py
"""
🎨 Exportador de PDF Ultra-Mejorado
Crea PDFs profesionales con:
- Diseño moderno y visual
- Información detallada del cliente/producto
- Totales destacados con colores
- Gráficos y tablas estilizadas
- Metadata completa
"""

from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String as ReportLabString
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF

from io import BytesIO
from datetime import datetime
from django.conf import settings


class AdvancedPDFExporter:
    """
    Exportador de PDF con capacidades avanzadas de diseño y visualización.
    """
    
    # Paleta de colores profesional
    COLORS = {
        'primary': colors.HexColor('#1A222E'),        # Azul oscuro
        'secondary': colors.HexColor('#4A5568'),      # Gris
        'accent': colors.HexColor('#3182CE'),         # Azul brillante
        'success': colors.HexColor('#38A169'),        # Verde
        'warning': colors.HexColor('#DD6B20'),        # Naranja
        'danger': colors.HexColor('#E53E3E'),         # Rojo
        'light_bg': colors.HexColor('#F7FAFC'),       # Gris muy claro
        'medium_bg': colors.HexColor('#E2E8F0'),      # Gris claro
        'white': colors.whitesmoke
    }
    
    def __init__(self, report_data, parsed_command):
        """
        Inicializa el exportador.
        
        Args:
            report_data (dict): Datos del reporte
            parsed_command (dict): Comando parseado con metadata
        """
        self.report_data = report_data
        self.parsed_command = parsed_command
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        self.story = []
    
    def _setup_custom_styles(self):
        """
        Configura estilos personalizados para el documento.
        """
        # Título principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.COLORS['primary'],
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtítulo
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.COLORS['secondary'],
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))
        
        # Encabezado de sección
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.COLORS['accent'],
            spaceBefore=15,
            spaceAfter=10,
            fontName='Helvetica-Bold',
            borderColor=self.COLORS['accent'],
            borderWidth=0,
            borderPadding=5
        ))
        
        # Metadata
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=self.COLORS['secondary'],
            alignment=TA_LEFT,
            fontName='Helvetica'
        ))
        
        # Totales
        self.styles.add(ParagraphStyle(
            name='TotalLabel',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=self.COLORS['primary'],
            fontName='Helvetica-Bold',
            alignment=TA_RIGHT
        ))
    
    def generate(self):
        """
        Genera el PDF completo y retorna un BytesIO.
        
        Returns:
            BytesIO: Buffer con el PDF generado
        """
        # Determinar orientación según número de columnas
        num_columns = len(self.report_data.get('headers', []))
        pagesize = landscape(letter) if num_columns > 6 else letter
        
        # Crear documento
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=pagesize,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50,
            title=self.report_data.get('title', 'Reporte'),
            author='Sistema de Reportes Inteligente'
        )
        
        # Construir contenido
        self._build_header()
        self._build_metadata_section()
        self._build_detected_entities()
        self._build_data_table()
        self._build_totals_section()
        self._build_footer()
        
        # Generar PDF
        doc.build(self.story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        self.buffer.seek(0)
        return self.buffer
    
    def _build_header(self):
        """
        Construye el encabezado del reporte con título y subtítulo.
        """
        # Título
        title = self.report_data.get('title', 'Reporte')
        title_para = Paragraph(title, self.styles['CustomTitle'])
        self.story.append(title_para)
        
        # Subtítulo
        subtitle = self.report_data.get('subtitle', '')
        if subtitle:
            subtitle_para = Paragraph(subtitle, self.styles['CustomSubtitle'])
            self.story.append(subtitle_para)
        
        # Espacio
        self.story.append(Spacer(1, 0.2 * inch))
    
    def _build_metadata_section(self):
        """
        Construye sección de metadata (fecha generación, filtros aplicados, etc.)
        """
        metadata = self.report_data.get('metadata', {})
        
        if metadata:
            # Tabla de metadata en 2 columnas
            meta_data = []
            
            # Fecha de generación
            gen_date = metadata.get('generado_en') or metadata.get('generated_at') or datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            meta_data.append(['Generado:', gen_date])
            
            # Período
            if metadata.get('periodo'):
                meta_data.append(['Período:', metadata['periodo']])
            
            # Cliente (si aplica)
            if metadata.get('cliente'):
                cliente_info = metadata['cliente']
                cliente_text = f"{cliente_info.get('nombre', cliente_info.get('username', 'N/A'))}"
                if cliente_info.get('email'):
                    cliente_text += f" ({cliente_info['email']})"
                meta_data.append(['Cliente:', cliente_text])
            
            # Producto (si aplica)
            if metadata.get('producto'):
                producto_info = metadata['producto']
                producto_text = producto_info.get('nombre', 'N/A')
                if producto_info.get('precio_actual'):
                    producto_text += f" - Precio: {producto_info['precio_actual']}"
                meta_data.append(['Producto:', producto_text])
            
            # Crear tabla
            meta_table = Table(meta_data, colWidths=[1.5*inch, 5*inch])
            meta_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (0, -1), self.COLORS['secondary']),
                ('TEXTCOLOR', (1, 0), (1, -1), self.COLORS['primary']),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            self.story.append(meta_table)
            self.story.append(Spacer(1, 0.3 * inch))
    
    def _build_detected_entities(self):
        """
        Muestra las entidades detectadas del comando (clientes, productos, etc.)
        """
        detected = self.parsed_command.get('detected_entities', {})
        
        if not detected:
            return
        
        entities_found = []
        
        # Clientes detectados
        if detected.get('clients'):
            clients = detected['clients']
            client_names = [c['username'] for c in clients]
            entities_found.append(['👤 Cliente(s):', ', '.join(client_names)])
        
        # Productos detectados
        if detected.get('products'):
            products = detected['products']
            product_names = [p['name'] for p in products[:3]]  # Máximo 3
            entities_found.append(['📦 Producto(s):', ', '.join(product_names)])
        
        # Categorías detectadas
        if detected.get('categories'):
            categories = detected['categories']
            category_names = [c['name'] for c in categories]
            entities_found.append(['🏷️ Categoría(s):', ', '.join(category_names)])
        
        # Rango de precio
        if detected.get('price_range'):
            pr = detected['price_range']
            if pr['type'] == 'between':
                price_text = f"${pr['min']} - ${pr['max']}"
            elif pr['type'] == 'more_than':
                price_text = f"Más de ${pr['min']}"
            else:
                price_text = f"Menos de ${pr['max']}"
            entities_found.append(['💰 Precio:', price_text])
        
        if entities_found:
            # Encabezado de sección
            section_header = Paragraph("Filtros Aplicados", self.styles['SectionHeader'])
            self.story.append(section_header)
            
            # Tabla de entidades
            entities_table = Table(entities_found, colWidths=[1.5*inch, 5*inch])
            entities_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (-1, -1), self.COLORS['primary']),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('BACKGROUND', (0, 0), (-1, -1), self.COLORS['light_bg']),
                ('BOX', (0, 0), (-1, -1), 1, self.COLORS['medium_bg']),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            self.story.append(entities_table)
            self.story.append(Spacer(1, 0.3 * inch))
    
    def _build_data_table(self):
        """
        Construye la tabla principal de datos.
        """
        headers = self.report_data.get('headers', [])
        rows = self.report_data.get('rows', [])
        
        if not headers or not rows:
            no_data_para = Paragraph("No hay datos para mostrar", self.styles['Normal'])
            self.story.append(no_data_para)
            return
        
        # Encabezado de sección
        section_header = Paragraph("Datos del Reporte", self.styles['SectionHeader'])
        self.story.append(section_header)
        
        # Preparar datos de la tabla
        table_data = [headers]
        
        # Limitar a 50 filas en la primera página (para evitar PDFs muy largos)
        displayed_rows = rows[:50]
        table_data.extend(displayed_rows)
        
        # Si hay más filas, agregar indicador
        if len(rows) > 50:
            table_data.append(['...'] * len(headers))
            table_data.append([f'Mostrando 50 de {len(rows)} registros'] + [''] * (len(headers) - 1))
        
        # Calcular anchos de columna dinámicamente
        num_cols = len(headers)
        available_width = 7.5 * inch  # Ancho disponible
        col_width = available_width / num_cols
        col_widths = [col_width] * num_cols
        
        # Crear tabla
        data_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Estilo de tabla profesional
        table_style = TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), self.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            # Filas de datos
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            
            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.5, self.COLORS['secondary']),
            ('BOX', (0, 0), (-1, -1), 1.5, self.COLORS['primary']),
            
            # Filas alternadas (cebra)
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.COLORS['light_bg']]),
        ])
        
        data_table.setStyle(table_style)
        
        self.story.append(data_table)
        self.story.append(Spacer(1, 0.3 * inch))
    
    def _build_totals_section(self):
        """
        Construye la sección de totales con diseño destacado.
        """
        totals = self.report_data.get('totals', {})
        
        if not totals:
            return
        
        # Encabezado de sección
        section_header = Paragraph("Totales y Resumen", self.styles['SectionHeader'])
        self.story.append(section_header)
        
        # Preparar datos de totales
        totals_data = []
        
        for key, value in totals.items():
            # Formatear etiqueta
            label = key.replace('_', ' ').title()
            totals_data.append([label + ':', str(value)])
        
        # Crear tabla de totals
        totals_table = Table(totals_data, colWidths=[3*inch, 2*inch])
        
        # Estilo destacado para totales
        totals_style = TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), self.COLORS['primary']),
            ('TEXTCOLOR', (1, 0), (1, -1), self.COLORS['accent']),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), self.COLORS['light_bg']),
            ('BOX', (0, 0), (-1, -1), 2, self.COLORS['accent']),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, self.COLORS['medium_bg']),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ])
        
        totals_table.setStyle(totals_style)
        
        self.story.append(totals_table)
        self.story.append(Spacer(1, 0.2 * inch))
    
    def _build_footer(self):
        """
        Construye el pie de página con información adicional.
        """
        # Interpretación del comando (si existe)
        interpretation = self.parsed_command.get('interpretation', '')
        if interpretation:
            footer_text = f"<i>Comando interpretado:</i><br/>{interpretation.replace(chr(10), '<br/>')}"
            footer_para = Paragraph(footer_text, self.styles['Metadata'])
            self.story.append(Spacer(1, 0.2 * inch))
            self.story.append(footer_para)
        
        # Confianza del parseo
        confidence = self.parsed_command.get('confidence', 0)
        if confidence > 0:
            confidence_text = f"<i>Confianza del análisis: {confidence*100:.0f}%</i>"
            confidence_para = Paragraph(confidence_text, self.styles['Metadata'])
            self.story.append(confidence_para)
    
    def _add_page_number(self, canvas_obj, doc):
        """
        Agrega número de página en el footer.
        """
        page_num = canvas_obj.getPageNumber()
        text = f"Página {page_num}"
        
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.setFillColor(self.COLORS['secondary'])
        canvas_obj.drawRightString(doc.pagesize[0] - 50, 30, text)
        canvas_obj.restoreState()


def export_to_advanced_pdf(report_data, parsed_command):
    """
    Función helper para exportar un reporte a PDF avanzado.
    
    Args:
        report_data (dict): Datos del reporte
        parsed_command (dict): Comando parseado con metadata
    
    Returns:
        BytesIO: Buffer con el PDF generado
    """
    exporter = AdvancedPDFExporter(report_data, parsed_command)
    return exporter.generate()
