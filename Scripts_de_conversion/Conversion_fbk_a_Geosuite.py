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
                    "PrismHeight": prism_height if prism_height is not None else 1.0,  # Predeterminado si no se encuentra PRISM
                    "Backsight": last_backsight,
                    "ObservationNumber": None,
                    "HorizontalAngle": None,
                    "SlopeDistance": None,
                    "ZenithDistance": None
                })
                bs_written = True
        elif line.startswith("AD") or line.startswith("ZD"):
            observation_number = parts[2]
            horizontal_angle = convert_to_gons(float(parts[3]))  # Convertir a gons
            slope_distance = float(parts[4])
            zenith_distance = convert_to_gons(float(parts[5]))  # Convertir a gons

            if last_backsight is not None:
                # Agregar la entrada RI del backsight primero, luego limpiar last_backsight
                data.append({
                    "Type": "RI",
                    "Station": current_station,
                    "InstrumentHeight": None,
                    "PrismHeight": prism_height if prism_height is not None else 1.0,
                    "Backsight": last_backsight,
                    "ObservationNumber": last_backsight,
                    "HorizontalAngle": 0.0,  # Ángulo horizontal predeterminado para backsight
                    "SlopeDistance": None,
                    "ZenithDistance": None
                })
                last_backsight = None

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

    return pd.DataFrame(data)

def convert_to_gons(angle):
    """Convierte un ángulo en notación topográfica (grados, minutos, segundos) a gons decimales."""
    degrees = int(angle)
    minutes = int((angle - degrees) * 100)
    seconds = (angle - degrees - minutes / 100) * 10000
    gons = (degrees + minutes / 60 + seconds / 3600) * (10 / 9)
    return round(gons, 6)

def format_field(value, width, align_right=True):
    """Formatea un campo para ajustarlo dentro de un ancho especificado."""
    if align_right:
        return f"{value:>{width}}"
    else:
        return f"{value:<{width}}"

def convert_fbk_to_mes(fbk_file_path, mes_file_path):
    df = convert_fbk_to_dataframe(fbk_file_path)

    mes_content = ["$$ME"]
    first_station_line = None  # Almacenamiento temporal para la primera línea de estación
    second_line_written = False  # Seguimiento de si se ha escrito la segunda línea

    for _, row in df.iterrows():
        if row["Type"] == "STN":
            # Formatear la línea de estación con InstrumentHeight, desplazada 1 espacio a la izquierda
            station_str = f"ST{row['Station']}"
            height_str = f"{row['InstrumentHeight']:.4f}"  # Formato con 4 decimales
            station_line = f"{station_str:<46}{height_str:>6}"  # Posición fija aplicada aquí

            if not second_line_written:
                # Almacenar temporalmente la primera línea de estación
                first_station_line = station_line
            else:
                # Escribir líneas de estación posteriores
                mes_content.append(station_line)

        elif row["Type"] == "BS" and not second_line_written:
            # Escribir la segunda línea (BS) y luego la primera línea de estación
            mes_content.append(f"ST{row['Backsight']:<52}")
            mes_content.append(first_station_line)
            first_station_line = None  # Limpiar el almacenamiento temporal
            second_line_written = True

        elif row["Type"] == "RI":
            # Excluir las líneas de RI correspondientes al BS si las observaciones son ZD
            if "ZD" not in df["Type"].values:
                mes_content.append(f"RI{row['ObservationNumber']:<6}{format_field(row['HorizontalAngle'], 28)}{format_field(row['PrismHeight'], 22)}")
        elif row["Type"] in ["AD", "ZD"]:
            # Reemplazar RI por AP si se trata de ZD (azimutes)
            prefix = "AP" if row["Type"] == "ZD" else "RI"
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
        koo_content.append(f"{int(row['Punto']):<8}{row['Este']:>36.4f}{row['Norte']:>11.4f}{row['Elevacion']:>13.4f}")

    # Agregar comentario para coordenadas aproximadas
    koo_content.append(";Coordenadas aproximadas")

    # Agregar coordenadas RADIACION o ESTACION
    for _, row in variable_coords.iterrows():
        koo_content.append(f"{int(row['Punto']):<8}{row['Este']:>36.4f}{row['Norte']:>11.4f}{row['Elevacion']:>13.4f}")

    with open(koo_file_path, 'w') as koo_file:
        koo_file.write("\n".join(koo_content))
