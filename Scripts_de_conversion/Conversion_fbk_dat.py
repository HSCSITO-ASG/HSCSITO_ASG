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
                angle = format_angle(parts[3])  # Convierte el ángulo horizontal o azimut
                distance = parts[4]
                vertical_angle = format_angle(parts[5])  # Convierte el ángulo vertical

                observation = (
                    observed_point,
                    angle,
                    distance,
                    vertical_angle,
                    instrument_height,
                    prism_height
                )

                if parts[0] == "AD":
                    current_observations.append(observation)
                    if backsight and observed_point != current_station:
                        radiations.append(
                            f"SS {backsight}-{current_station}-{observed_point} {angle} {distance} {vertical_angle} {instrument_height}/{prism_height}"
                        )
                elif parts[0] == "ZD":
                    general_observations.append(
                        f"BM {current_station}-{observed_point} {angle} {distance} {vertical_angle} {instrument_height}/{prism_height}"
                    )

        if current_station and current_observations:
            polygonal_data.append((current_station, backsight, current_observations))

    return polygonal_data, radiations, general_observations

# Función para filtrar la poligonal principal
def filter_polygonal(polygonal_data):
    filtered_polygonal = []

    # Incluir el primer TB basado en el primer backsight
    if polygonal_data:
        first_bs = polygonal_data[0][1]
        filtered_polygonal.append(f"TB {first_bs}")

    # Agregar observaciones que conectan STN principales
    for i in range(len(polygonal_data) - 1):
        current_stn, _, current_observations = polygonal_data[i]
        next_stn, _, _ = polygonal_data[i + 1]

        for obs in current_observations:
            observed_point, angle, distance, vertical_angle, instrument_height, prism_height = obs
            if observed_point == next_stn:  # Conexión entre STN actuales
                filtered_polygonal.append(
                    f"T {current_stn} {angle} {distance} {vertical_angle} {instrument_height}/{prism_height}"
                )

    # Incluir la última observación de la última STN
    if polygonal_data and polygonal_data[-1][2]:
        last_stn, _, last_observations = polygonal_data[-1]
        last_obs = last_observations[-1]
        observed_point, angle, distance, vertical_angle, instrument_height, prism_height = last_obs
        filtered_polygonal.append(
            f"T {last_stn} {angle} {distance} {vertical_angle} {instrument_height}/{prism_height}"
        )

    # Incluir el cierre con TE basado en el último punto observado
    if polygonal_data and polygonal_data[-1][2]:
        last_point = polygonal_data[-1][2][-1][0]
        filtered_polygonal.append(f"TE {last_point}")

    return filtered_polygonal

# Función para filtrar radiaciones innecesarias
def filter_radiations(radiations, polygonal_data):
    if len(polygonal_data) < 2:
        return radiations  # Si no hay suficientes datos de poligonal, no se filtran radiaciones

    polygonal_combinations = set()
    for i in range(len(polygonal_data) - 1):
        current_stn = polygonal_data[i][0]
        next_stn = polygonal_data[i + 1][0]
        if i == 0:
            polygonal_combinations.add((polygonal_data[i][1], current_stn, next_stn))
        else:
            polygonal_combinations.add((polygonal_data[i - 1][0], current_stn, next_stn))
    polygonal_combinations.add((polygonal_data[-2][0], polygonal_data[-1][0], polygonal_data[-1][2][-1][0]))

    filtered_radiations = []
    for rad in radiations:
        parts = rad.split()
        key = tuple(parts[1].split('-'))
        if key not in polygonal_combinations:
            # Intercambiar el orden de los dos primeros valores en radiaciones
            swapped_key = f"{key[1]}-{key[0]}-{key[2]}"
            filtered_radiations.append(rad.replace(parts[1], swapped_key))

    return filtered_radiations

# Función para generar el archivo DAT
def generate_dat_file(csv_path, fbk_path, output_dat_path):
    csv_coordinates = read_csv_coordinates(csv_path)
    polygonal_data, radiations, general_observations = process_fbk_observations(fbk_path)

    with open(output_dat_path, "w") as dat_file:
        # Escribir coordenadas
        dat_file.write("# Coordenadas\n")
        for coord in csv_coordinates:
            dat_file.write(f"{coord}\n")

        # Escribir poligonal principal si existe
        if polygonal_data:
            dat_file.write("\n# Poligonal Principal\n")
            filtered_polygonal = filter_polygonal(polygonal_data)
            for line in filtered_polygonal:
                dat_file.write(f"{line}\n")

            # Escribir radiaciones si hay poligonal principal
            dat_file.write("\n# Radiaciones\n")
            filtered_radiations = filter_radiations(radiations, polygonal_data)
            for rad in filtered_radiations:
                dat_file.write(f"{rad}\n")
        
        # Escribir observaciones generales (ZD)
        if general_observations:
            dat_file.write("\n# Observaciones Generales\n")
            for obs in general_observations:
                dat_file.write(f"{obs}\n")

# Función para convertir ángulos de notación topográfica a GMS
def format_angle(angle):
    degrees = int(float(angle))
    minutes = int((float(angle) - degrees) * 100)
    seconds = round((((float(angle) - degrees) * 100) - minutes) * 100, 2)
    return f"{degrees}-{minutes:02d}-{seconds:05.2f}"

