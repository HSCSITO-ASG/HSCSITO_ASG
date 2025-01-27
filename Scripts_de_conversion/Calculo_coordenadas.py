import pandas as pd
import math

def fbk_a_coordenadas(ruta_fbk, N_base, E_base, Z_base, N_amarre, E_amarre, Z_amarre, estacion_inicial, estacion_amarre, ruta_resumida):
    def convert_topographic_angle(angle_topo):
        degrees = int(angle_topo)
        minutes = int((angle_topo - degrees) * 100)
        seconds = ((angle_topo - degrees) * 100 - minutes) * 100
        return degrees, minutes, seconds

    def topographic_to_decimal(degrees, minutes, seconds):
        return degrees + (minutes / 60) + (seconds / 3600)

    def calcular_coordenadas(N_a, E_a, Z_a, Di_a_b, Zen_a_b, Az_a_b, A_i, A_p):
        N_b = Di_a_b * math.sin(Zen_a_b) * math.cos(Az_a_b) + N_a
        E_b = Di_a_b * math.sin(Zen_a_b) * math.sin(Az_a_b) + E_a
        Z_b = Di_a_b * math.cos(Zen_a_b) + Z_a + A_i - A_p
        return N_b, E_b, Z_b

    def calcular_azimut_inicial(N_a, E_a, N_b, E_b):
        delta_E = E_b - E_a
        delta_N = N_b - N_a
        azimut_radians = math.atan2(delta_E, delta_N)
        azimut_degrees = math.degrees(azimut_radians)
        if azimut_degrees < 0:
            azimut_degrees += 360
        return azimut_degrees

    def calcular_azimut_siguiente(azimut_inicial, angulo_horizontal, n):
        azimut_siguiente = azimut_inicial + angulo_horizontal - (n * 180)
        if azimut_siguiente < 0:
            azimut_siguiente += 360
        elif azimut_siguiente >= 360:
            azimut_siguiente -= 360
        return azimut_siguiente

    def leer_fbk_desde_archivo(ruta_fbk):
        with open(ruta_fbk, 'r') as file:
            return file.readlines()

    fbk_data = leer_fbk_desde_archivo(ruta_fbk)
    coordenadas_base = {'N': N_base, 'E': E_base, 'Z': Z_base}
    coordenadas_amarre = {'N': N_amarre, 'E': E_amarre, 'Z': Z_amarre}

    coordenadas = {estacion_inicial: (coordenadas_base['N'], coordenadas_base['E'], coordenadas_base['Z'])}
    N_a, E_a, Z_a = coordenadas_base['N'], coordenadas_base['E'], coordenadas_base['Z']
    N_b, E_b, Z_b = coordenadas_amarre['N'], coordenadas_amarre['E'], coordenadas_amarre['Z']

    A_i, A_p = 0, 0
    azimut_inicial = calcular_azimut_inicial(N_b, E_b, N_a, E_a)
    n_estacion = 0

    azimutes_por_estacion = {}
    resultados = []
    estaciones = set()

    for linea in fbk_data:
        try:
            partes = linea.strip().split()
            if len(partes) == 0:
                continue
            if partes[0] == "STN":
                est_id = int(partes[1])
                estaciones.add(est_id)
                A_i = float(partes[2])
                if est_id not in azimutes_por_estacion:
                    n_estacion += 1
                if est_id in azimutes_por_estacion:
                    azimut_inicial = azimutes_por_estacion[est_id]
                if est_id in coordenadas:
                    N_a, E_a, Z_a = coordenadas[est_id]
                resultados.append([est_id, "STN", A_i, A_p, N_a, E_a, Z_a, "", "", "", "", "", "", ""])
            elif partes[0] == "PRISM":
                A_p = float(partes[1])
            elif partes[0] in ["ZD", "AD"] and partes[1] == "VA":
                punto_id = int(partes[2])
                angulo_topo = float(partes[3])
                distancia_inclinada = float(partes[4])
                angulo_zenital_topo = float(partes[5])
                descripcion = partes[6] if len(partes) > 6 else ""

                Zen_degrees, Zen_minutes, Zen_seconds = convert_topographic_angle(angulo_zenital_topo)
                Zen_a_b_decimal = topographic_to_decimal(Zen_degrees, Zen_minutes, Zen_seconds)
                Zen_a_b = math.radians(Zen_a_b_decimal)

                if partes[0] == "AD":
                    Az_degrees, Az_minutes, Az_seconds = convert_topographic_angle(angulo_topo)
                    Az_a_b_decimal = topographic_to_decimal(Az_degrees, Az_minutes, Az_seconds)
                    azimut_siguiente = calcular_azimut_siguiente(azimut_inicial, Az_a_b_decimal, n_estacion)
                    Az_a_b = math.radians(azimut_siguiente)
                    azimut_decimal = azimut_siguiente
                else:
                    Az_degrees, Az_minutes, Az_seconds = convert_topographic_angle(angulo_topo)
                    Az_a_b_decimal = topographic_to_decimal(Az_degrees, Az_minutes, Az_seconds)
                    Az_a_b = math.radians(Az_a_b_decimal)
                    azimut_decimal = Az_a_b_decimal

                N_b, E_b, Z_b = calcular_coordenadas(N_a, E_a, Z_a, distancia_inclinada, Zen_a_b, Az_a_b, A_i, A_p)
                coordenadas[punto_id] = (N_b, E_b, Z_b)
                resultados.append([punto_id, "OBS", A_i, A_p, N_a, E_a, Z_a, distancia_inclinada, azimut_decimal, Zen_a_b_decimal, N_b, E_b, Z_b, descripcion])
                if partes[0] == "AD":
                    azimutes_por_estacion[punto_id] = math.degrees(Az_a_b)
        except Exception as e:
            print(f"Error procesando línea: {linea}. Detalles: {e}")

    df_resultados = pd.DataFrame(resultados, columns=[
        'Punto', 'Tipo', 'Altura Instrumental', 'Altura Prisma', 'Norte_anterior', 'Este_anterior', 'Elevacion_anterior', 
        'Distancia inclinada', 'Azimut (decimal)', 'Angulo Zenital (decimal)', 
        'Norte', 'Este', 'Elevacion', 'Descripcion'
    ])

    fila_amarre = {
        'Punto': estacion_amarre, 'Tipo': 'ORIENT', 'Altura Instrumental': '', 'Altura Prisma': '', 
        'Norte_anterior': '', 'Este_anterior': '', 'Elevacion_anterior': '', 'Distancia inclinada': '',  
        'Azimut (decimal)': '', 'Angulo Zenital (decimal)': '', 'Norte': coordenadas_amarre['N'],
        'Este': coordenadas_amarre['E'], 'Elevacion': coordenadas_amarre['Z'], 'Descripcion': 'Orientacion'
    }

    fila_estacion_inicial = {
        'Punto': estacion_inicial, 'Tipo': 'FIJO', 'Altura Instrumental': '', 'Altura Prisma': '',
        'Norte_anterior': coordenadas_base['N'], 'Este_anterior': coordenadas_base['E'], 'Elevacion_anterior': coordenadas_base['Z'],
        'Distancia inclinada': '', 'Azimut (decimal)': '', 'Angulo Zenital (decimal)': '',
        'Norte': coordenadas_base['N'], 'Este': coordenadas_base['E'], 'Elevacion': coordenadas_base['Z'],
        'Descripcion': 'Estacion inicial'
    }

    df_resultados = pd.concat([pd.DataFrame([fila_amarre]), pd.DataFrame([fila_estacion_inicial]), df_resultados], ignore_index=True)

    if estacion_inicial not in df_resultados['Punto'].values:
        df_resultados = pd.concat([pd.DataFrame([fila_estacion_inicial]), df_resultados], ignore_index=True)

    if estacion_inicial in df_resultados['Punto'].values:
        df_resultados.loc[df_resultados['Punto'] == estacion_inicial, ['Norte', 'Este', 'Elevacion', 'Descripcion']] = [
            coordenadas_base['N'], coordenadas_base['E'], coordenadas_base['Z'], 'Estacion inicial']

    df_resultados['Tipo_punto'] = 'RADIACION'
    df_resultados.loc[df_resultados['Punto'] == estacion_inicial, 'Tipo_punto'] = 'CONTROL'
    df_resultados.loc[df_resultados['Punto'] == estacion_amarre, 'Tipo_punto'] = 'CONTROL'
    df_resultados.loc[(df_resultados['Punto'].isin(estaciones)) & (df_resultados['Tipo_punto'] != 'CONTROL'), 'Tipo_punto'] = 'ESTACION'

    df_resultados.to_csv(ruta_resumida, index=False)

    df_resumido = df_resultados[['Punto', 'Norte', 'Este', 'Elevacion', 'Tipo_punto', 'Descripcion']].drop_duplicates(subset=['Punto'])

    if estacion_inicial not in df_resumido['Punto'].values:
        fila_inicio = {
            'Punto': estacion_inicial,
            'Norte': coordenadas_base['N'],
            'Este': coordenadas_base['E'],
            'Elevacion': coordenadas_base['Z'],
            'Tipo_punto': 'CONTROL',
            'Descripcion': 'Estacion inicial'
        }
        df_resumido = pd.concat([df_resumido, pd.DataFrame([fila_inicio])], ignore_index=True)

    if estacion_inicial in df_resumido['Punto'].values:
        df_resumido.loc[df_resumido['Punto'] == estacion_inicial, ['Norte', 'Este', 'Elevacion', 'Descripcion']] = [
            coordenadas_base['N'], coordenadas_base['E'], coordenadas_base['Z'], 'Estacion inicial']

    df_resumido = df_resumido.drop_duplicates(subset=['Punto']).sort_values(by='Punto').reset_index(drop=True)

    df_resumido.to_csv(ruta_resumida, index=False)

    return df_resultados, df_resumido

