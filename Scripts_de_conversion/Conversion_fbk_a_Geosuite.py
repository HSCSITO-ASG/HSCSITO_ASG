import pandas as pd

def convert_fbk_to_dataframe(fbk_file_path):
    with open(fbk_file_path, 'r') as fbk_file:
        lines = fbk_file.readlines()

    data = []
    current_station = None
    prism_height = None
    last_backsight = None
    bs_written = False  # Seguimiento de si se ha escrito la línea BS ST

    for line in lines:
        parts = line.strip().split()
        if line.startswith("STN"):
            current_station = parts[1]
            instrument_height = float(parts[2])
            data.append({
                "Type": "STN",
                "Station": current_station,
                "InstrumentHeight": instrument_height,
                "PrismHeight": prism_height,
                "Backsight": None,
                "ObservationNumber": None,
                "HorizontalAngle": None,
                "SlopeDistance": None,
                "ZenithDistance": None
            })
            bs_written = False  # Reiniciar para cada nueva estación
        elif line.startswith("PRISM"):
            prism_height = float(parts[1])
        elif line.startswith("BS"):
            last_backsight = parts[1]
            if not bs_written:
                data.append({
                    "Type": "BS",
                    "Station": current_station,
                    "InstrumentHeight": None,
                    "PrismHeight": prism_height if prism_height is not None else 1.0,
                    "Backsight": last_backsight,
                    "ObservationNumber": None,
                    "HorizontalAngle": None,
                    "SlopeDistance": None,
                    "ZenithDistance": None
                })
                bs_written = True
        elif line.startswith("AD") or line.startswith("ZD"):
            observation_number = parts[2]
            
            # Convertir los ángulos a grados decimales
            horizontal_angle = convert_to_gons(extract_angle(parts[3]))  # Convertir a gons
            slope_distance = float(parts[4])
            zenith_distance = convert_to_gons(extract_angle(parts[5]))  # Convertir a gons

            if last_backsight is not None:
                reference_ri = {
                    "Type": "RI",
                    "Station": current_station,
                    "InstrumentHeight": None,
                    "PrismHeight": prism_height if prism_height is not None else 1.0,
                    "Backsight": last_backsight,
                    "ObservationNumber": last_backsight,
                    "HorizontalAngle": 0.0,  # Ángulo horizontal predeterminado para backsight
                    "SlopeDistance": None,
                    "ZenithDistance": None
                }
                last_backsight = None
            else:
                reference_ri = None

            # Si la observación es ZD, no agregamos el RI de orientación
            if line.startswith("AD"):
                data.append(reference_ri) if reference_ri else None
            data.append({
                "Type": "ZD" if line.startswith("ZD") else "AD",
                "Station": current_station,
                "InstrumentHeight": None,
                "PrismHeight": prism_height if prism_height is not None else 1.0,
                "Backsight": None,
                "ObservationNumber": observation_number,
                "HorizontalAngle": horizontal_angle,
                "SlopeDistance": slope_distance,
                "ZenithDistance": zenith_distance
            })

    return pd.DataFrame([entry for entry in data if entry])

def extract_angle(angle_str):
    """Extrae el ángulo en notación topográfica (grados, minutos, segundos) y lo convierte a grados decimales."""
    # Convertir el ángulo a flotante para manipulación
    angle = str(angle_str).strip()

    # Extraemos los grados, minutos, segundos y decimales de segundos
    negative, degrees, minutes, seconds, decimal_seconds = format_topographic_angle(angle)

    # Convertimos el ángulo a grados decimales
    decimal_degrees = convert_to_decimal(degrees, minutes, seconds, decimal_seconds)

    return decimal_degrees

def format_topographic_angle(angle):
    """Función para separar un ángulo de notación topográfica en grados, minutos, segundos"""
    # Convertir el ángulo a flotante para manipulación
    angle = str(angle).strip()  # Convertir el ángulo a string para manipulación

    # Verificar si el ángulo tiene signo negativo
    negative = "-" if angle.startswith("-") else ""
    if negative:
        angle = angle[1:]  # Eliminar el signo para manejar la parte positiva

    # Asegurarse de que el ángulo tiene al menos 4 dígitos después del punto decimal
    if '.' not in angle:
        angle += ".00000"

    # Dividir el ángulo en partes
    degrees = int(angle.split('.')[0])  # Parte entera, que son los grados
    decimal_part = angle.split('.')[1]  # Parte decimal
    
    # Extraer los minutos, segundos y decimales de segundos
    minutes = int(decimal_part[:2])  # Los dos primeros dígitos después del punto decimal son los minutos
    seconds = int(decimal_part[2:4])  # Los dos siguientes dígitos después de los minutos son los segundos
    decimal_seconds = int(decimal_part[4]) if len(decimal_part) > 4 else 0  # El siguiente dígito es el decimal de los segundos

    # Retornar el ángulo en formato GMS
    return negative, degrees, minutes, seconds, decimal_seconds

def convert_to_decimal(degrees, minutes, seconds, decimal_seconds):
    """Convierte los grados, minutos, segundos y decimales de segundos a grados decimales"""
    return degrees + (minutes / 60) + (seconds / 3600) + (decimal_seconds / 36000)

def convert_to_gons(decimal_degrees):
    """Convierte los grados decimales a gones decimales"""
    return round(decimal_degrees * (10 / 9), 6)

def format_field(value, width, align_right=True):
    """Formatea un campo para ajustarlo dentro de un ancho especificado."""
    if align_right:
        return f"{value:>{width}}"
    else:
        return f"{value:<{width}}"

def convert_fbk_to_mes(fbk_file_path, mes_file_path):
    df = convert_fbk_to_dataframe(fbk_file_path)

    mes_content = ["$$ME"]
    reference_ri = None  # Almacena el primer RI de la estación con el valor correcto

    for index, row in df.iterrows():
        if row["Type"] == "STN":
            station_str = f"ST{row['Station']}"
            height_str = f"{row['InstrumentHeight']:.4f}"
            station_line = f"{station_str:<46}{height_str:>6}"
            mes_content.append(station_line)
            reference_ri = None  # Resetear el RI de referencia
        
        elif row["Type"] == "RI":
            reference_ri = f"RI{row['ObservationNumber']:<6}{format_field(row['HorizontalAngle'], 28)}{format_field(row['PrismHeight'], 22)}"
        
        elif row["Type"] in ["AD", "ZD"]:
            prefix = "AP" if row["Type"] == "ZD" else "RI"
            if reference_ri and row["Type"] == "AD":  # Solo agregamos el RI si es AD
                mes_content.append(reference_ri)  # Asegurar que el RI de referencia aparece antes de cada observación
            mes_content.append(f"{prefix}{row['ObservationNumber']:<6}{format_field(row['HorizontalAngle'], 28)}{format_field(row['PrismHeight'], 22)}")
            mes_content.append(f"ZD{row['ObservationNumber']:<6}{format_field(row['ZenithDistance'], 28)}{format_field(row['PrismHeight'], 22)}")
            mes_content.append(f"DS{row['ObservationNumber']:<6}{format_field(row['SlopeDistance'], 28)}{format_field(row['PrismHeight'], 22)}")

    with open(mes_file_path, 'w') as mes_file:
        mes_file.write("\n".join(mes_content))


def convert_csv_to_koo(csv_file_path, koo_file_path):
    df = pd.read_csv(csv_file_path)

    # Actualización de tipos de coordenadas
    fixed_coords = df[df['Tipo_punto'] == 'CONTROL']
    variable_coords = df[(df['Tipo_punto'] == 'RADIACION') | (df['Tipo_punto'] == 'ESTACION')]

    koo_content = ["$$PK"]

    # Agregar coordenadas CONTROL
    for _, row in fixed_coords.iterrows():
        koo_content.append(f"{int(row['Punto']):<8}{row['Este']:>36.4f}{row['Norte']:>11.4f}{row['Elevacion']:>14.4f}")

    # Agregar comentario para coordenadas aproximadas
    koo_content.append(";Coordenadas aproximadas")

    # Agregar coordenadas RADIACION o ESTACION
    for _, row in variable_coords.iterrows():
        koo_content.append(f"{int(row['Punto']):<8}{row['Este']:>36.4f}{row['Norte']:>11.4f}{row['Elevacion']:>14.4f}")

    with open(koo_file_path, 'w') as koo_file:
        koo_file.write("\n".join(koo_content))
