import os
import pandas as pd
from qgis.core import (
    QgsVectorLayer,
    QgsFields,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsVectorFileWriter
)
from PyQt5.QtCore import QVariant

def generate_shp_files(csv_path, output_shp_path_points=None, output_shp_path_lines=None):
    """
    Genera archivos SHP de puntos y líneas a partir de un archivo CSV.

    :param csv_path: Ruta del archivo CSV de entrada.
    :param output_shp_path_points: Ruta de salida para el archivo SHP de puntos (opcional).
    :param output_shp_path_lines: Ruta de salida para el archivo SHP de líneas (opcional).
    """
    if output_shp_path_points is None:
        output_shp_path_points = os.path.splitext(csv_path)[0] + ".shp"
    if output_shp_path_lines is None:
        output_shp_path_lines = os.path.splitext(csv_path)[0] + "_lineas.shp"

    # Leer el archivo CSV
    csv_data = pd.read_csv(csv_path)

    # Verificar si las columnas necesarias existen
    if not all(col in csv_data.columns for col in ['Norte', 'Este', 'Elevacion', 'Tipo_punto', 'Descripcion']):
        raise ValueError("El archivo CSV debe contener las columnas 'Norte', 'Este', 'Elevacion', 'Tipo_punto' y 'Descripcion'.")

    # Crear una capa vectorial de puntos
    temp_layer_points = QgsVectorLayer("Point?crs=EPSG:4326", "Coordenadas_NEZ", "memory")

    # Definir los campos para puntos
    fields_points = QgsFields()
    fields_points.append(QgsField("Punto", QVariant.Int))
    fields_points.append(QgsField("Elevacion", QVariant.Double))
    fields_points.append(QgsField("Tipo_punto", QVariant.String))
    fields_points.append(QgsField("Descripcion", QVariant.String))

    # Añadir los campos a la capa de puntos
    provider_points = temp_layer_points.dataProvider()
    provider_points.addAttributes(fields_points)
    temp_layer_points.updateFields()

    # Crear características a partir de las coordenadas de puntos
    features_points = []
    for index, row in csv_data.iterrows():
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(row['Este'], row['Norte'])))
        feature.setAttributes([
            row['Punto'],
            row['Elevacion'],
            row['Tipo_punto'],
            row['Descripcion']
        ])
        features_points.append(feature)

    # Añadir características a la capa de puntos
    provider_points.addFeatures(features_points)
    temp_layer_points.updateExtents()

    # Guardar la capa de puntos como un archivo SHP
    error_points = QgsVectorFileWriter.writeAsVectorFormat(
        temp_layer_points,
        output_shp_path_points,
        "UTF-8",
        driverName="ESRI Shapefile"
    )

    if error_points == QgsVectorFileWriter.NoError:
        print(f"Archivo SHP de puntos guardado correctamente en: {output_shp_path_points}")
    else:
        print("Error al guardar el archivo SHP de puntos.")

    # Crear una capa vectorial de líneas
    temp_layer_lines = QgsVectorLayer("LineString?crs=EPSG:4326", "Lineas_CONTROL_ESTACION", "memory")

    # Definir los campos para líneas
    fields_lines = QgsFields()
    fields_lines.append(QgsField("ID", QVariant.Int))

    # Añadir los campos a la capa de líneas
    provider_lines = temp_layer_lines.dataProvider()
    provider_lines.addAttributes(fields_lines)
    temp_layer_lines.updateFields()

    # Crear una línea conectando puntos según los criterios definidos
    line_feature = QgsFeature()
    points = []

    # Seleccionar el primer punto (CONTROL y Orientacion)
    start_point = csv_data[(csv_data['Tipo_punto'] == 'CONTROL') & (csv_data['Descripcion'] == 'Orientacion')]
    if not start_point.empty:
        row = start_point.iloc[0]
        points.append(QgsPointXY(row['Este'], row['Norte']))

    # Seleccionar el segundo punto (CONTROL y Estacion inicial)
    second_point = csv_data[(csv_data['Tipo_punto'] == 'CONTROL') & (csv_data['Descripcion'] == 'Estacion inicial')]
    if not second_point.empty:
        row = second_point.iloc[0]
        points.append(QgsPointXY(row['Este'], row['Norte']))

    # Añadir los puntos restantes (STN en orden de "Punto")
    stn_points = csv_data[csv_data['Tipo_punto'] == 'ESTACION'].sort_values(by='Punto')
    for _, row in stn_points.iterrows():
        points.append(QgsPointXY(row['Este'], row['Norte']))

    if len(points) > 1:
        line_feature.setGeometry(QgsGeometry.fromPolylineXY(points))
        line_feature.setAttributes([1])
        provider_lines.addFeatures([line_feature])
    temp_layer_lines.updateExtents()

    # Guardar la capa de líneas como un archivo SHP
    error_lines = QgsVectorFileWriter.writeAsVectorFormat(
        temp_layer_lines,
        output_shp_path_lines,
        "UTF-8",
        driverName="ESRI Shapefile"
    )

    if error_lines == QgsVectorFileWriter.NoError:
        print(f"Archivo SHP de líneas guardado correctamente en: {output_shp_path_lines}")
    else:
        print("Error al guardar el archivo SHP de líneas.")

