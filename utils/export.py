"""
Utilitaires d'export : PDF (ReportLab) et CSV
"""
import csv
import io
from datetime import datetime


def export_tournees_csv(tournees: list) -> bytes:
    """
    Génère un fichier CSV des tournées
    Retourne les bytes du CSV
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    # En-tête
    writer.writerow([
        'ID', 'Nom', 'Camion', 'Date', 'Heure Départ',
        'Statut', 'Nb Points', 'Distance (km)',
        'Durée (min)', 'CO2 (kg)', 'Coût (MAD)', 'Optimisée'
    ])

    for t in tournees:
        writer.writerow([
            t.get('id'), t.get('nom'), t.get('camion', ''),
            t.get('date_tournee'), t.get('heure_depart'),
            t.get('statut'), t.get('nb_points'),
            t.get('distance_km'), t.get('duree_min'),
            t.get('co2_kg'), t.get('cout_mad'),
            'Oui' if t.get('optimisee') else 'Non'
        ])

    return output.getvalue().encode('utf-8-sig')  # BOM pour Excel


def export_tournees_pdf(tournees: list, stats: dict = None) -> bytes:
    """
    Génère un rapport PDF des tournées avec ReportLab
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph,
            Spacer, HRFlowable
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        return b'ReportLab non disponible'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                  alignment=TA_CENTER, textColor=colors.HexColor('#1a3a5c'))
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'],
                                     alignment=TA_CENTER, textColor=colors.grey)

    elements = []

    # En-tête
    elements.append(Paragraph('RAPPORT DES TOURNÉES DE COLLECTE', title_style))
    elements.append(Paragraph(f'Agadir — {datetime.now().strftime("%d/%m/%Y %H:%M")}', subtitle_style))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor('#27ae60')))
    elements.append(Spacer(1, 0.5*cm))

    # Statistiques globales
    if stats:
        stats_data = [
            ['Indicateur', 'Valeur'],
            ['Distance totale', f"{stats.get('distance_totale_km', 0)} km"],
            ['Émissions CO2', f"{stats.get('co2_total_kg', 0)} kg"],
            ['Coût total', f"{stats.get('cout_total_mad', 0)} MAD"],
            ['Tournées terminées', f"{stats.get('tournees_terminees', 0)}"],
        ]
        stats_table = Table(stats_data, colWidths=[8*cm, 8*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3a5c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4f8')]),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 0.8*cm))

    # Tableau des tournées
    if tournees:
        elements.append(Paragraph('Détail des Tournées', styles['Heading2']))
        elements.append(Spacer(1, 0.3*cm))

        headers = ['Nom', 'Camion', 'Date', 'Points', 'Dist. km', 'CO2 kg', 'Statut']
        data = [headers]
        for t in tournees:
            data.append([
                str(t.get('nom', ''))[:30],
                str(t.get('camion', '')),
                str(t.get('date_tournee', '')),
                str(t.get('nb_points', 0)),
                f"{t.get('distance_km', 0):.1f}",
                f"{t.get('co2_kg', 0):.2f}",
                str(t.get('statut', '')),
            ])

        col_widths = [5*cm, 3*cm, 2.5*cm, 1.8*cm, 2*cm, 2*cm, 2.5*cm]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(table)

    # Pied de page
    elements.append(Spacer(1, 1*cm))
    elements.append(HRFlowable(width='100%', thickness=1, color=colors.grey))
    elements.append(Paragraph(
        'Système d\'Optimisation des Tournées de Collecte — Agadir',
        subtitle_style
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
