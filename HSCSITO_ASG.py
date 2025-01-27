# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HSCSITO_ASG
                                 A QGIS plugin
 Tratamiento de observaciones convencionales de Estaciones Totales en QGIS.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-12-12
        git sha              : $Format:%H$
        copyright            : (C) 2024 by Alexandra Giseth Flor Avilez, Juan Esteban Guzmán Martínez
        email                : alexandraavilez267@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import sys
import re
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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QFileDialog

# Import from local scripts
from .Scripts_de_conversion.Archivo_crudo_fbk import process_data
from .Scripts_de_conversion.Calculo_coordenadas import fbk_a_coordenadas
from .Scripts_de_conversion.Conversion_fbk_dat import generate_dat_file
from .Scripts_de_conversion.Conversion_fbk_a_Geosuite import convert_fbk_to_mes, convert_csv_to_koo
from .Scripts_de_conversion.Coordenadas_a_Capa_V import generate_shp_files



# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .HSCSITO_ASG_dialog import HSCSITO_ASGDialog
from .HSCSITO_ASG_dialog import HSCSITO_ASGDialog_2
from .HSCSITO_ASG_dialog import HSCSITO_ASGDialog_3
from .HSCSITO_ASG_dialog import HSCSITO_ASGDialog_4
import os.path


class HSCSITO_ASG:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'HSCSITO_ASG_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&HSCSITO_ASG')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('HSCSITO_ASG', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Cree las entradas del menú y los iconos de la barra de herramientas dentro del QGIS GUI."""

        icon_path = ':/plugins/HSCSITO_ASG/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Convertir archivo crudo de observaciones a libro de campo (.fbk)'),
            callback=self.run,
            parent=self.iface.mainWindow())
        icon_path_1 = ':/plugins/HSCSITO_ASG/icons/coord.png'
        self.add_action(
            icon_path_1,  # Ruta del icono
            text="Convertir libro de campo (.fbk) a Coordenadas xyz",
            callback=self.run_fbk_a_coordenadas,  # Conecta con la función correcta
            parent=self.iface.mainWindow())
        icon_path_2 = ':/plugins/HSCSITO_ASG/icons/coord3.png'
        self.add_action(
            icon_path_2,  # Ruta del icono
            text="Convertir libro de campo (.fbk) a Starnet (.dat)",
            callback=self.run_fbk_a_starnet,  # Conecta con la función correcta
            parent=self.iface.mainWindow())
        icon_path_3 = ':/plugins/HSCSITO_ASG/icons/coord2.png'
        self.add_action(
            icon_path_3,  # Ruta del icono
            text="Convertir libro de campo (.fbk) a Geosuite (.mes y .koo)",
            callback=self.run_fbk_a_geosuite,  # Conecta con la función correcta
            parent=self.iface.mainWindow())             
        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&HSCSITO_ASG'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Método que realiza todo el trabajo principal"""

        # Crear el cuadro de diálogo con elementos y mantener la referencia
        # Solo crear la GUI UNA VEZ en el callback, para que solo se cargue cuando se inicie el plugin
        if self.first_start == True:
            self.first_start = False
            self.dlg = HSCSITO_ASGDialog()

        # Asegurarse de que el cuadro de diálogo permanezca encima de la interfaz de QGIS
        self.dlg.setWindowModality(Qt.ApplicationModal)

        # Asegurarse de que la lista desplegable esté vacía antes de agregar elementos
        self.dlg.fontComboBox.clear()

        # Llenar la lista principal con opciones
        self.dlg.fontComboBox.addItems([
            "Geomax.GSI",
            "Sanding.GSI",
            "South_362_33",
            "South_362_66",
            "South_345",
        ])

        # Llenar fontComboBox_obs con Azimutes y Ángulos horarios
        self.dlg.fontComboBox_obs.clear()
        self.dlg.fontComboBox_obs.addItems([
            "Azimutes",
            "Ángulos horarios",
        ])

        # Conectar el botón processButton para ejecutar la función principal
        self.dlg.processButton.clicked.connect(self.execute_conversion)

        # Conectar el botón processButton_2 para regenerar el archivo FBK
        self.dlg.processButton_2.clicked.connect(self.regenerate_fbk)

        # Conectar toolButton_salida para abrir un cuadro de diálogo para guardar el archivo de salida
        self.dlg.toolButton_salida.clicked.connect(self.select_output_file)

        # Conectar los cambios en el archivo de entrada a la previsualización
        self.dlg.mQgsFileWidget_input.fileChanged.connect(self.preview_input_file)

        # Inicializar la barra de progreso
        self.dlg.progressBar.setValue(0)

        # Mostrar el cuadro de diálogo
        self.dlg.show()
        # Ejecutar el bucle de eventos del cuadro de diálogo
        result = self.dlg.exec_()
        # Comprobar si se presionó OK
        if result:
            pass

    def execute_conversion(self):
        """Ejecutar el proceso de conversión basado en las opciones seleccionadas."""
        input_file = self.dlg.mQgsFileWidget_input.filePath()
        output_file = self.dlg.lineEdit_salida.text()
        method = self.dlg.fontComboBox.currentText()
        observation_type = self.dlg.fontComboBox_obs.currentText()

        if not input_file or not output_file or not method:
            QMessageBox.critical(self.dlg, "Error", "Por favor, especifique el archivo de entrada, archivo de salida y el método.")
            return

        try:
            from .Scripts_de_conversion.Archivo_crudo_fbk import process_data

            # Iniciar la conversión y actualizar la barra de progreso
            process_data(input_file, method, output_file)
            
            # Si el tipo de observación es "Azimutes", reemplazar AD con ZD en el archivo de salida
            if observation_type == "Azimutes":
                self.modify_output_file(output_file)

            # Previsualizar el archivo de salida
            self.preview_output_file(output_file)

            self.dlg.progressBar.setValue(100)
            QMessageBox.information(self.dlg, "Éxito", "¡Conversión completada con éxito!")
        except Exception as e:
            self.dlg.progressBar.setValue(0)
            QMessageBox.critical(self.dlg, "Error", f"Ocurrió un error: {e}")

    def modify_output_file(self, file_path):
        """Modificar el archivo de salida reemplazando AD con ZD."""
        try:
            with open(file_path, 'r') as file:
                content = file.read()

            # Reemplazar AD con ZD
            modified_content = content.replace("AD", "ZD")

            with open(file_path, 'w') as file:
                file.write(modified_content)
        except Exception as e:
            QMessageBox.critical(self.dlg, "Error", f"No se pudo modificar el archivo de salida: {e}")

    def select_output_file(self):
        """Abrir un cuadro de diálogo para seleccionar la ruta del archivo de salida y establecerlo en lineEdit_salida."""
        file_path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "Seleccionar archivo de salida",
            "",
            "Archivos FBK (*.fbk)"
        )

        if file_path:
            self.dlg.lineEdit_salida.setText(file_path)

    def preview_input_file(self):
        """Previsualizar el contenido del archivo de entrada en textEdit_preview."""
        input_file = self.dlg.mQgsFileWidget_input.filePath()
        if not input_file:
            self.dlg.textEdit_preview.setPlainText("No se seleccionó ningún archivo.")
            return

        try:
            with open(input_file, 'r') as file:
                content = file.read()
                self.dlg.textEdit_preview.setPlainText(content)
        except Exception as e:
            self.dlg.textEdit_preview.setPlainText(f"Error al leer el archivo: {e}")

    def preview_output_file(self, file_path):
        """Previsualizar el contenido del archivo de salida en textEdit_fbk."""
        if not file_path:
            self.dlg.textEdit_fbk.setPlainText("No se generó ningún archivo de salida.")
            return

        try:
            with open(file_path, 'r') as file:
                content = file.read()
                self.dlg.textEdit_fbk.setPlainText(content)
        except Exception as e:
            self.dlg.textEdit_fbk.setPlainText(f"Error al leer el archivo de salida: {e}")

    def regenerate_fbk(self):
        """Regenerar el archivo FBK si el usuario ha realizado modificaciones."""
        output_file = self.dlg.lineEdit_salida.text()
        modified_content = self.dlg.textEdit_fbk.toPlainText()

        if not output_file:
            QMessageBox.warning(self.dlg, "Advertencia", "No se ha generado ningún archivo de salida para regenerar.")
            return

        try:
            # Sobrescribir el archivo de salida con el contenido modificado
            with open(output_file, 'w') as file:
                file.write(modified_content)

            QMessageBox.information(self.dlg, "Éxito", "¡El archivo de salida se ha regenerado correctamente!")
        except Exception as e:
            QMessageBox.critical(self.dlg, "Error", f"No se pudo regenerar el archivo de salida: {e}")


    def run_fbk_a_coordenadas(self):
        """Método para ejecutar FBK a Coordenadas"""

        # Crear el diálogo con elementos (después de la traducción) y mantener la referencia
        # Solo crear la interfaz gráfica UNA VEZ en el callback, para que solo se cargue cuando se inicie el plugin
        if not hasattr(self, 'dlg_2') or self.dlg_2 is None:
            self.dlg_2 = HSCSITO_ASGDialog_2()

        # Conectar mQgsFileWidget_input_fb para establecer el archivo de entrada
        self.dlg_2.mQgsFileWidget_input_fb.fileChanged.connect(self.set_input_file)

        # Conectar mQgsFileWidget_fb_2 para manejar la ruta del archivo de salida
        self.dlg_2.mQgsFileWidget_fb_2.fileChanged.connect(self.set_output_file_fb_2)

        # Establecer archivo de salida predeterminado si existe
        self.set_default_output_file_fb_2()

        # Conectar toolButton_salida_fb para abrir un diálogo de guardado de archivo
        self.dlg_2.toolButton_salida_fb.clicked.connect(self.select_output_file_2)

        # Conectar pushButton_cl_fb para limpiar los valores de la tabla
        self.dlg_2.pushButton_cl_fb.clicked.connect(self.clear_table)

        # Conectar pushButton_ej para ejecutar la herramienta
        self.dlg_2.pushButton_ej.clicked.connect(self.execute_tool)

        # Conectar pushButton_validar_fb para validar cambios en textEdit_preview_fb
        self.dlg_2.pushButton_validar_fb.clicked.connect(self.validate_fbk_modifications)

        # Conectar toolButton_salida_fb_2 y lineEdit_salida_fb_2 para el shapefile de puntos
        self.dlg_2.toolButton_salida_fb_2.clicked.connect(self.select_point_shapefile)

        # Conectar toolButton_salida_fb_3 y lineEdit_salida_fb_3 para el shapefile de polilíneas
        self.dlg_2.toolButton_salida_fb_3.clicked.connect(self.select_polyline_shapefile)

        # Conectar pushButton_ej_fb_2 para ejecutar la generación de shapefiles
        self.dlg_2.pushButton_ej_fb_2.clicked.connect(self.execute_shapefile_generation)

        # Inicializar lineEdit_salida_fb para mostrar la ruta del archivo de salida seleccionado
        self.dlg_2.lineEdit_salida_fb.setText("")

        # Mostrar el diálogo
        self.dlg_2.show()

    def set_input_file(self):
        """Establecer el archivo de entrada desde mQgsFileWidget_input_fb."""
        input_file = self.dlg_2.mQgsFileWidget_input_fb.filePath()

        # Cargar contenido en textEdit_preview_fb
        try:
            with open(input_file, 'r') as file:
                content = file.read()
            self.dlg_2.textEdit_preview_fb.setPlainText(content)
        except Exception as e:
            QMessageBox.critical(self.dlg_2, "Error", f"No se pudo cargar el contenido del archivo: {e}")

    def set_output_file_fb_2(self):
        """Manejar cambios en mQgsFileWidget_fb_2 y validar su contenido."""
        output_file = self.dlg_2.mQgsFileWidget_fb_2.filePath()
        if not output_file:
            QMessageBox.warning(self.dlg_2, "Salida inválida", "Por favor, seleccione una ruta válida para el archivo de salida.")
            return

        # Validar la existencia y el formato del archivo
        if not os.path.isfile(output_file) or not output_file.endswith('.csv'):
            QMessageBox.warning(self.dlg_2, "Archivo inválido", "El archivo seleccionado debe ser un archivo CSV válido.")
            return

        QMessageBox.information(self.dlg_2, "Archivo cargado", f"El archivo {output_file} se cargó correctamente.")

    def set_default_output_file_fb_2(self):
        """Establecer la ruta del archivo de salida predeterminada en mQgsFileWidget_fb_2 desde lineEdit_salida_fb."""
        output_file = self.dlg_2.lineEdit_salida_fb.text()
        if output_file and os.path.isfile(output_file) and output_file.endswith('.csv'):
            self.dlg_2.mQgsFileWidget_fb_2.setFilePath(output_file)

    def select_output_file_2(self):
        """Abrir un diálogo de archivo para seleccionar la ruta del archivo de salida."""
        output_file, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "Guardar archivo CSV",
            "",
            "Archivos CSV (*.csv)"
        )

        if output_file:
            self.dlg_2.lineEdit_salida_fb.setText(output_file)

    def select_point_shapefile(self):
        """Seleccionar la ruta del archivo de salida para el shapefile de puntos."""
        point_shapefile, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "Guardar shapefile de puntos",
            "",
            "Shapefiles (*.shp)"
        )

        if point_shapefile:
            self.dlg_2.lineEdit_salida_fb_2.setText(point_shapefile)

    def select_polyline_shapefile(self):
        """Seleccionar la ruta del archivo de salida para el shapefile de polilíneas."""
        polyline_shapefile, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "Guardar shapefile de polilíneas",
            "",
            "Shapefiles (*.shp)"
        )

        if polyline_shapefile:
            self.dlg_2.lineEdit_salida_fb_3.setText(polyline_shapefile)

    def clear_table(self):
        """Limpiar todos los valores del widget de la tabla."""
        table = self.dlg_2.tableWidget_fb
        for row in range(table.rowCount()):
            for column in range(table.columnCount()):
                table.setItem(row, column, None)

    def validate_fbk_modifications(self):
        """Validar y guardar las modificaciones realizadas en textEdit_preview_fb."""
        input_file = self.dlg_2.mQgsFileWidget_input_fb.filePath()
        if not input_file:
            QMessageBox.warning(self.dlg_2, "Entrada inválida", "No se seleccionó ningún archivo de entrada para validar las modificaciones.")
            return

        try:
            # Simular el proceso de validación
            self.dlg_2.progressBar_fb_2.setValue(0)
            with open(input_file, 'w') as file:
                modified_content = self.dlg_2.textEdit_preview_fb.toPlainText()
                file.write(modified_content)
            self.dlg_2.progressBar_fb_2.setValue(100)
            QMessageBox.information(self.dlg_2, "Validación exitosa", "Las modificaciones al archivo de entrada se han guardado correctamente.")
        except Exception as e:
            self.dlg_2.progressBar_fb_2.setValue(0)
            QMessageBox.critical(self.dlg_2, "Error", f"No se pudieron guardar las modificaciones: {e}")

    def execute_tool(self):
        """Recopilar parámetros y ejecutar la función fbk_a_coordenadas."""
        input_file = self.dlg_2.mQgsFileWidget_input_fb.filePath()
        output_file = self.dlg_2.lineEdit_salida_fb.text()

        if not input_file or not output_file:
            QMessageBox.warning(self.dlg_2, "Información faltante", "Por favor, proporcione las rutas de los archivos de entrada y salida.")
            return

        try:
            from .Scripts_de_conversion.Calculo_coordenadas import fbk_a_coordenadas

            # Obtener valores del widget de la tabla
            table = self.dlg_2.tableWidget_fb
            param_8 = float(table.item(0, 0).text()) if table.item(0, 0) and self.is_float(table.item(0, 0).text()) else None
            param_9 = float(table.item(1, 0).text()) if table.item(1, 0) and self.is_float(table.item(1, 0).text()) else None
            param_5 = float(table.item(0, 1).text()) if table.item(0, 1) and self.is_float(table.item(0, 1).text()) else None
            param_2 = float(table.item(1, 1).text()) if table.item(1, 1) and self.is_float(table.item(1, 1).text()) else None
            param_6 = float(table.item(0, 2).text()) if table.item(0, 2) and self.is_float(table.item(0, 2).text()) else None
            param_3 = float(table.item(1, 2).text()) if table.item(1, 2) and self.is_float(table.item(1, 2).text()) else None
            param_7 = float(table.item(0, 3).text()) if table.item(0, 3) and self.is_float(table.item(0, 3).text()) else None
            param_4 = float(table.item(1, 3).text()) if table.item(1, 3) and self.is_float(table.item(1, 3).text()) else None

            # Validar que se proporcionen todos los parámetros necesarios
            if None in (param_2, param_3, param_4, param_5, param_6, param_7, param_8, param_9):
                QMessageBox.critical(self.dlg_2, "Error", "Faltan algunos valores en la tabla o son inválidos.")
                return

            # Ejecutar la función fbk_a_coordenadas
            self.dlg_2.progressBar_fb.setValue(0)
            fbk_a_coordenadas(
                input_file,  # Parámetro 1
                param_2,    # Parámetro 2
                param_3,    # Parámetro 3
                param_4,    # Parámetro 4
                param_5,    # Parámetro 5
                param_6,    # Parámetro 6
                param_7,    # Parámetro 7
                param_9,    # Parámetro 8
                param_8,    # Parámetro 9
                output_file  # Parámetro 10
            )
            self.dlg_2.progressBar_fb.setValue(100)
            QMessageBox.information(self.dlg_2, "Éxito", f"Archivo convertido y guardado en {output_file}.")
        except Exception as e:
            self.dlg_2.progressBar_fb.setValue(0)
            QMessageBox.critical(self.dlg_2, "Error", f"Ocurrió un error: {e}")

    def is_float(self, value):
        """Comprobar si un valor es un número flotante."""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def execute_shapefile_generation(self):
        """Ejecutar el proceso de generación de shapefiles de forma independiente."""
        point_shapefile = self.dlg_2.lineEdit_salida_fb_2.text()
        polyline_shapefile = self.dlg_2.lineEdit_salida_fb_3.text()
        csv_file = self.dlg_2.mQgsFileWidget_fb_2.filePath()

        if not csv_file or not point_shapefile or not polyline_shapefile:
            QMessageBox.warning(self.dlg_2, "Información faltante", "Por favor, proporcione todas las rutas de los archivos requeridos.")
            return

        try:
            from .Scripts_de_conversion.Coordenadas_a_Capa_V import generate_shp_files

            self.dlg_2.progressBar_fb_3.setValue(0)

            # Generar shapefiles
            generate_shp_files(csv_file, point_shapefile, polyline_shapefile)

            self.dlg_2.progressBar_fb_3.setValue(100)
            QMessageBox.information(self.dlg_2, "Éxito", "Los shapefiles se generaron correctamente.")
        except Exception as e:
            self.dlg_2.progressBar_fb_3.setValue(0)
            QMessageBox.critical(self.dlg_2, "Error", f"Ocurrió un error: {e}")

    def run_fbk_a_starnet(self):
        """Método para ejecutar la conversión de FBK a Starnet"""

        # Crear el cuadro de diálogo con elementos y mantener la referencia
        # Solo crear la interfaz gráfica UNA VEZ en el callback, para que solo se cargue cuando se inicie el plugin
        if not hasattr(self, 'dlg_3') or self.dlg_3 is None:
            self.dlg_3 = HSCSITO_ASGDialog_3()

        # Conectar mQgsFileWidget_input_d para establecer el archivo FBK de entrada
        self.dlg_3.mQgsFileWidget_input_d.fileChanged.connect(self.set_input_fbk_file)

        # Conectar mQgsFileWidget_input_d_2 para establecer el archivo CSV de entrada
        self.dlg_3.mQgsFileWidget_input_d_2.fileChanged.connect(self.set_input_csv_file)

        # Conectar toolButton_salida_d para abrir un cuadro de diálogo para guardar el archivo DAT de salida
        self.dlg_3.toolButton_salida_d.clicked.connect(self.select_output_dat_file)

        # Conectar processButton_d para ejecutar la herramienta
        self.dlg_3.processButton_d.clicked.connect(self.execute_conversion_4)

        # Inicializar progressBar_d a cero
        self.dlg_3.progressBar_d.setValue(0)

        # Mostrar el cuadro de diálogo
        self.dlg_3.show()

    def set_input_fbk_file(self):
        """Cargar el contenido del archivo FBK seleccionado en textEdit_preview_d."""
        input_file_3 = self.dlg_3.mQgsFileWidget_input_d.filePath()
        if not input_file_3:
            QMessageBox.warning(self.dlg_3, "Entrada inválida", "Por favor, seleccione un archivo FBK válido.")
            return

        try:
            with open(input_file_3, 'r') as file:
                content = file.read()
            self.dlg_3.textEdit_preview_d.setPlainText(content)
        except Exception as e:
            QMessageBox.critical(self.dlg_3, "Error", f"No se pudo cargar el contenido del archivo: {e}")

    def set_input_csv_file(self):
        """Validar el archivo CSV seleccionado."""
        input_file_3 = self.dlg_3.mQgsFileWidget_input_d_2.filePath()
        if not input_file_3 or not input_file_3.endswith('.csv'):
            QMessageBox.warning(self.dlg_3, "Entrada inválida", "Por favor, seleccione un archivo CSV válido.")

    def select_output_dat_file(self):
        """Abrir un cuadro de diálogo para seleccionar la ruta del archivo DAT de salida."""
        output_file, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "Guardar archivo DAT",
            "",
            "Archivos DAT (*.dat)"
        )

        if output_file:
            self.dlg_3.lineEdit_salida_d.setText(output_file)

    def execute_conversion_4(self):
        """Ejecutar la conversión de FBK a Starnet."""
        fbk_file = self.dlg_3.mQgsFileWidget_input_d.filePath()
        csv_file = self.dlg_3.mQgsFileWidget_input_d_2.filePath()
        output_file = self.dlg_3.lineEdit_salida_d.text()

        if not fbk_file or not csv_file or not output_file:
            QMessageBox.warning(self.dlg_3, "Información faltante", "Por favor, proporcione todas las rutas de los archivos requeridos.")
            return

        try:
            from .Scripts_de_conversion.Conversion_fbk_dat import generate_dat_file

            self.dlg_3.progressBar_d.setValue(0)
            generate_dat_file(csv_file, fbk_file, output_file)

            # Cargar el contenido del archivo DAT generado en textEdit_d_2
            with open(output_file, 'r') as file:
                dat_content = file.read()
            self.dlg_3.textEdit_d_2.setPlainText(dat_content)

            self.dlg_3.progressBar_d.setValue(100)
            QMessageBox.information(self.dlg_3, "Éxito", "La generación del archivo DAT se completó correctamente.")
        except Exception as e:
            self.dlg_3.progressBar_d.setValue(0)
            QMessageBox.critical(self.dlg_3, "Error", f"Ocurrió un error: {e}")

    def run_fbk_a_geosuite(self):
        """Método para ejecutar la conversión de FBK a Geosuite"""

        # Crear el cuadro de diálogo con elementos y mantener la referencia
        # Solo crear la interfaz gráfica UNA VEZ en el callback, para que solo se cargue cuando se inicie el plugin
        if not hasattr(self, 'dlg_4') or self.dlg_4 is None:
            self.dlg_4 = HSCSITO_ASGDialog_4()

        # Conectar mQgsFileWidget_input_g para establecer el archivo FBK de entrada
        self.dlg_4.mQgsFileWidget_input_g.fileChanged.connect(self.set_input_fbk_file_g)

        # Conectar mQgsFileWidget_input_g_2 para establecer el archivo CSV de entrada
        self.dlg_4.mQgsFileWidget_input_g_2.fileChanged.connect(self.set_input_csv_file_g)

        # Conectar toolButton_salida_g para abrir un cuadro de diálogo para guardar el archivo MES de salida
        self.dlg_4.toolButton_salida_g.clicked.connect(self.select_output_mes_file)

        # Conectar toolButton_salida_g_2 para abrir un cuadro de diálogo para guardar el archivo KOO de salida
        self.dlg_4.toolButton_salida_g_2.clicked.connect(self.select_output_koo_file)

        # Conectar processButton_g para ejecutar la herramienta
        self.dlg_4.processButton_g.clicked.connect(self.execute_geosuite_conversion)

        # Inicializar progressBar_g a cero
        self.dlg_4.progressBar_g.setValue(0)

        # Mostrar el cuadro de diálogo
        self.dlg_4.show()

    def set_input_fbk_file_g(self):
        """Cargar el contenido del archivo FBK seleccionado en textEdit_preview_g."""
        input_file = self.dlg_4.mQgsFileWidget_input_g.filePath()
        if not input_file:
            QMessageBox.warning(self.dlg_4, "Entrada inválida", "Por favor, seleccione un archivo FBK válido.")
            return

        try:
            with open(input_file, 'r') as file:
                content = file.read()
            self.dlg_4.textEdit_preview_g.setPlainText(content)
        except Exception as e:
            QMessageBox.critical(self.dlg_4, "Error", f"No se pudo cargar el contenido del archivo: {e}")

    def set_input_csv_file_g(self):
        """Validar el archivo CSV seleccionado."""
        input_file = self.dlg_4.mQgsFileWidget_input_g_2.filePath()
        if not input_file or not input_file.endswith('.csv'):
            QMessageBox.warning(self.dlg_4, "Entrada inválida", "Por favor, seleccione un archivo CSV válido.")

    def select_output_mes_file(self):
        """Abrir un cuadro de diálogo para seleccionar la ruta del archivo MES de salida."""
        output_file, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "Guardar archivo MES",
            "",
            "Archivos MES (*.mes)"
        )

        if output_file:
            self.dlg_4.lineEdit_salida_g.setText(output_file)

    def select_output_koo_file(self):
        """Abrir un cuadro de diálogo para seleccionar la ruta del archivo KOO de salida."""
        output_file, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "Guardar archivo KOO",
            "",
            "Archivos KOO (*.koo)"
        )

        if output_file:
            self.dlg_4.lineEdit_salida_g_2.setText(output_file)

    def execute_geosuite_conversion(self):
        """Ejecutar las conversiones de FBK a MES y CSV a KOO."""
        fbk_file = self.dlg_4.mQgsFileWidget_input_g.filePath()
        csv_file = self.dlg_4.mQgsFileWidget_input_g_2.filePath()
        mes_file = self.dlg_4.lineEdit_salida_g.text()
        koo_file = self.dlg_4.lineEdit_salida_g_2.text()

        if not fbk_file or not csv_file or not mes_file or not koo_file:
            QMessageBox.warning(self.dlg_4, "Información faltante", "Por favor, proporcione todas las rutas de los archivos requeridos.")
            return

        try:
            from .Scripts_de_conversion.Conversion_fbk_a_Geosuite import convert_fbk_to_mes, convert_csv_to_koo

            self.dlg_4.progressBar_g.setValue(0)

            # Convertir FBK a MES
            convert_fbk_to_mes(fbk_file, mes_file)
            self.dlg_4.progressBar_g.setValue(50)

            # Convertir CSV a KOO
            convert_csv_to_koo(csv_file, koo_file)
            self.dlg_4.progressBar_g.setValue(100)

            # Cargar el contenido de los archivos MES y KOO generados en sus respectivos widgets textEdit
            with open(mes_file, 'r') as file:
                mes_content = file.read()
            self.dlg_4.textEdit_g_2.setPlainText(mes_content)

            with open(koo_file, 'r') as file:
                koo_content = file.read()
            self.dlg_4.textEdit_g.setPlainText(koo_content)

            QMessageBox.information(self.dlg_4, "Éxito", "La generación de archivos Geosuite se completó correctamente.")
        except Exception as e:
            self.dlg_4.progressBar_g.setValue(0)
            QMessageBox.critical(self.dlg_4, "Error", f"Ocurrió un error: {e}")

