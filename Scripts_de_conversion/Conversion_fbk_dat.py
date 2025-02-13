import pandas as pd

# Función para leer coordenadas desde CSV
def read_csv_coordinates(csv_path):
    df = pd.read_csv(csv_path)
    coordinates = []
    for index, row in df.iterrows():
        tipo = "! ! !" if row["Tipo_punto"] == "CONTROL" else ""
        # Redondear las coordenadas a 4 decimales
        norte = round(row["Norte"], 4)
        este = round(row["Este"], 4)
        elevacion = round(row["Elevacion"], 4)
        descripcion = f" '{row['Descripcion']}" if 'Descripcion' in row else ""
        coordinates.append(f"C {int(row['Punto'])} {norte} {este} {elevacion} {tipo}{descripcion}")
    return coordinates

# Función para procesar observaciones del FBK
def process_fbk_observations(fbk_path):
    polygonal_data = []
    radiations = []
    general_observations = []

    with open(fbk_path, "r") as fbk_file:
        lines = fbk_file.readlines()
        current_station = None
        backsight = None
        instrument_height = None
        prism_height = None
        current_observations = []

        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue

            if parts[0] == "STN":
                if current_station and current_observations:
                    polygonal_data.append((current_station, backsight, current_observations))
                current_station = parts[1]
                instrument_height = parts[2]
                current_observations = []
            elif parts[0] == "BS":
                backsight = parts[1]
            elif parts[0] == "PRISM":
                prism_height = parts[1]
            elif parts[0] in {"AD", "ZD"}:  # Procesar tanto AD como ZD
                observed_point = parts[2]
                angle = format_topographic_angle(parts[3])  # Convierte el ángulo horizontal o azimut
                distance = parts[4]
                vertical_angle = format_topographic_angle(parts[5])  # Aplica el mismo formato a los ángulos verticales

                observation = (
                    observed_point,
                    angle,
                    distance,
                    vertical_angle,
                    instrument_height,
                    prism_height
                )

                if parts[0] == "AD":
                    general_observations.append(
                        f"M {current_station}-{backsight}-{observed_point} {angle} {distance} {vertical_angle} {instrument_height}/{prism_height}"
                    )
                else:
                    general_observations.append(
                        f"BM {current_station}-{observed_point} {angle} {distance} {vertical_angle} {instrument_height}/{prism_height}"
                    )

        if current_station and current_observations:
            polygonal_data.append((current_station, backsight, current_observations))

    return polygonal_data, radiations, general_observations

# Función para generar el archivo DAT
def generate_dat_file(csv_path, fbk_path, output_dat_path):
    csv_coordinates = read_csv_coordinates(csv_path)
    polygonal_data, radiations, general_observations = process_fbk_observations(fbk_path)

    with open(output_dat_path, "w") as dat_file:
        # Escribir coordenadas
        dat_file.write("# Coordenadas\n")
        for coord in csv_coordinates:
            dat_file.write(f"{coord}\n")

        # Escribir observaciones generales (ZD y AD)
        if general_observations:
            dat_file.write("\n# Observaciones Generales\n")
            for obs in general_observations:
                dat_file.write(f"{obs}\n")

# Función para convertir ángulos de notación topográfica a GMS (extracción estricta)
def format_topographic_angle(angle):
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
    degrees = angle.split('.')[0]  # Parte entera, que son los grados
    decimal_part = angle.split('.')[1]  # Parte decimal
    
    # Extraer los minutos, segundos y decimales de los segundos
    minutes = decimal_part[:2]  # Los dos primeros dígitos después del punto decimal son los minutos
    seconds = decimal_part[2:4]  # Los dos siguientes dígitos después de los minutos son los segundos
    decimal_seconds = decimal_part[4] if len(decimal_part) > 4 else '0'  # El siguiente dígito es el decimal de los segundos

    # Eliminar ceros innecesarios: Aplicar solo para los grados
    degrees = str(int(degrees))  # Asegurarse de que grados no tenga ceros innecesarios
    minutes = minutes.zfill(2)  # Los minutos siempre deben tener 2 dígitos
    seconds = seconds.zfill(2)  # Los segundos siempre deben tener 2 dígitos
    decimal_seconds = str(int(decimal_seconds))  # Asegurarse de que los decimales de segundos no tengan ceros innecesarios

    # Retornar el ángulo en formato GMS
    return f"{negative}{degrees}-{minutes}-{seconds}.{decimal_seconds}"

