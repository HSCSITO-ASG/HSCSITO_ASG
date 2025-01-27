import os
import re

# Función para procesar archivos Geomax.GSI
def process_geomax_gsi(input_path, output_path):
    def extract_value_by_scanning(line, identifier):
        start = line.find(identifier)
        if start != -1:
            start += len(identifier)
            for i in range(start, len(line)):
                if line[i] == '+':
                    value = line[i+1:i+17].strip()
                    return value.lstrip('0') if value else None
        return None

    def extract_prism_value(line):
        start = line.find("87...0+")
        if start != -1:
            start += len("87...0+")
            prism_value = line[start:start+16].strip()
            prism_value = ''.join([c for c in prism_value if c.isdigit()])
            return str(float(prism_value) / 1000) if prism_value else None
        return None

    def extract_angle_value(part):
        try:
            value = part[-8:]  # Extract the last 8 digits
            degrees = int(value[:3])
            decimals = value[3:]  # Remaining part after degrees
            formatted_value = f"{degrees}.{decimals}"  # Combine degrees and decimals directly
            return formatted_value
        except ValueError:
            return "0.000000"

    def extract_distance_value(part):
        try:
            value = part[5:].lstrip('0')
            if value == '' or value == '+':
                return 0.0
            return float(value) / 1000.0
        except ValueError:
            return 0.0

    def extract_point_name(part):
        try:
            return int(part[-4:])  # Modified to consider the last 4 characters for larger values
        except ValueError:
            return 0

    def extract_description(gsi_lines, index):
        if index > 0 and gsi_lines[index - 1].startswith("*41"):
            desc_line = gsi_lines[index - 1]
            description = desc_line[9:25].lstrip('0').strip()  # Extract description without leading zeros
            return description if description else 'p'
        return 'p'

    def cumple_condicion(line):
        required_identifiers = ["*11", "21", "22", "31", "51", "87", "81", "82", "83"]
        return all(identifier in line for identifier in required_identifiers)

    def process_gsi_file(gsi_lines):
        fbk_lines = []
        prism_value = None
        add_prism_after_stn_bs = False

        for i, line in enumerate(gsi_lines):
            if "*11" in line and "84" in line and "85" in line and "86" in line and "88" in line:
                station = extract_value_by_scanning(line, "*11")
                height = extract_value_by_scanning(line, "88")
                if height:
                    height = str(float(height) / 1000)
                if station and height and i + 1 < len(gsi_lines):
                    bs_line = gsi_lines[i + 1]
                    if "*11" in bs_line and "81" in bs_line and "82" in bs_line and "83" in bs_line:
                        bs = extract_value_by_scanning(bs_line, "*11")
                        if bs:
                            fbk_lines.append(f"STN {station} {height}\n")
                            fbk_lines.append(f"BS {bs}\n")
                            add_prism_after_stn_bs = True

            if "87...0+" in line:
                prism_value = extract_prism_value(line)

            if add_prism_after_stn_bs and prism_value:
                fbk_lines.append(f'PRISM {prism_value}\n')
                add_prism_after_stn_bs = False

            if cumple_condicion(line):
                parts = line.split()
                if len(parts) > 3:
                    point_name = extract_point_name(parts[0])
                    ha = extract_angle_value(parts[1])
                    va = extract_angle_value(parts[2])
                    sd = extract_distance_value(parts[3]) if len(parts) > 3 else 0.0
                    description = extract_description(gsi_lines, i)
                    fbk_lines.append(f'AD VA {point_name} {ha} {sd:.3f} {va} {description}\n')

        return fbk_lines

    with open(input_path, 'r') as file:
        gsi_lines = file.readlines()

    fbk_lines = process_gsi_file(gsi_lines)

    with open(output_path, 'w') as file:
        file.writelines(fbk_lines)

    print(f"Archivo FBK generado en: {output_path}")


# Función para procesar archivos Sanding.GSI
def process_sanding_gsi(input_path, output_path):
    def extract_angle_value(part):
        try:
            value = part[10:].lstrip('0')
            if value == '':
                return "0.00000"
            if len(value) == 8:
                value = value[:3] + '.' + value[3:]
            elif len(value) == 7:
                value = value[:2] + '.' + value[2:]
            return value
        except ValueError:
            return "0.00000"

    def extract_distance_value(part):
        try:
            value = part[5:].lstrip('0')
            if value == '' or value == '+':
                return 0.0
            return float(value) / 1000.0
        except ValueError:
            return 0.0

    def extract_point_name(part):
        try:
            value = part[10:].lstrip('0').strip()
            return value
        except ValueError:
            return ""

    def extract_significant_value(part, scale=1):
        try:
            value = part[5:].lstrip('0')
            if value == '' or value == '+':
                return 0.0
            return float(value) / scale
        except ValueError:
            return 0.0

    def format_prism_height(part):
        try:
            value = part[5:].lstrip('0')
            if value == '' or value == '+':
                return "0.000"
            return f"{float(value) / 1000:.3f}".replace(',', '.')
        except ValueError:
            return "0.000"

    def get_descriptions(gsi_lines):
        descriptions = {}
        for i, line in enumerate(gsi_lines):
            if line.startswith('*41'):
                parts = line.split()
                desc_id = parts[0][5:9]
                description = parts[0][16:].strip('0').strip()
                if description:
                    descriptions[desc_id] = description
        return descriptions

    def process_gsi_to_fbk(gsi_lines):
        fbk_lines = []
        descriptions = get_descriptions(gsi_lines)
        stn_current = None
        target = None
        in_ocupar = False
        prism_added = False

        for i, line in enumerate(gsi_lines):
            try:
                if line.startswith('*41....+0000000000OCUPAR'):
                    parts = line.split()
                    stn_current = parts[1][10:].lstrip('0') or '0'
                    hi = extract_distance_value(parts[7])
                    fbk_lines.append(f'STN {stn_current} {hi:.3f}\n')
                    in_ocupar = True
                    prism_added = False
                elif line.startswith('*41....+00000000000000RE'):
                    parts = line.split()
                    target = parts[1][10:].lstrip('0') or '0'
                    if stn_current and target:
                        fbk_lines.append(f'BS {target}\n')
                    in_ocupar = False
                elif line.startswith('*42'):
                    parts = line.split()
                    if target is None:
                        target = parts[0][10:].lstrip('0') or '0'
                    if stn_current and target and not in_ocupar:
                        fbk_lines.append(f'BS {target}\n')
                elif line.startswith('*11'):
                    parts = line.split()
                    point_name = extract_point_name(parts[0])
                    desc_id = gsi_lines[i - 1][5:9] if i > 0 and gsi_lines[i - 1].startswith('*41') else None
                    description = descriptions.get(desc_id, "")
                    if point_name == target:
                        continue
                    ha = extract_angle_value(parts[1])
                    va = extract_angle_value(parts[2])
                    sd = extract_distance_value(parts[3])
                    e_obj = extract_significant_value(parts[4])
                    n_obj = extract_significant_value(parts[5])
                    elev = extract_significant_value(parts[6])
                    hr = format_prism_height(parts[7])

                    if not prism_added:
                        fbk_lines.append(f'PRISM {hr}\n')
                        prism_added = True

                    observation_line = f'AD VA {point_name} {ha} {sd:.3f} {va}'
                    if description:
                        observation_line += f' {description}'
                    fbk_lines.append(observation_line + '\n')

            except IndexError:
                print(f"Skipping line due to IndexError: {line}")
            except Exception as e:
                print(f"Error processing line: {line}\n{e}")

        return fbk_lines

    with open(input_path, 'r') as file:
        gsi_lines = file.readlines()

    fbk_lines = process_gsi_to_fbk(gsi_lines)

    with open(output_path, 'w') as file:
        file.writelines(fbk_lines)

    print(f"Archivo FBK generado en: {output_path}")


# Función para procesar archivos South_345
def process_south_345(input_path, output_path):
    def parse_line(line):
        return line.strip().replace("     ", ",").split(",")

    def create_fbk_nts(data):
        fbk_lines = []
        current_station = None
        current_prism_height = None

        for i, row in enumerate(data):
            if row[0] == "STN":
                current_station = row[1]
                current_description = row[3]
                for j in range(i + 1, len(data)):
                    if data[j][0] == "SS":
                        current_prism_height = data[j][2]
                        break
                fbk_lines.append(f"STN\t{row[1]}\t{row[2]}\n")
            elif row[0] == "BKB" and len(row) >= 3:
                fbk_lines.append(f"BS\t{row[1]}\n")
                fbk_lines.append(f"PRISM\t{current_prism_height}\n")
            elif row[0] == "SS" and i + 3 < len(data):
                point_id = row[1]
                current_prism_height = row[2]
                description = row[3] if len(row) > 3 else ""
                next_row_hv = data[i + 1]
                next_row_hd = data[i + 2]
                next_row_sd = data[i + 3]
                if next_row_hv[0] == "HV" and next_row_hd[0] == "HD" and next_row_sd[0] == "SD":
                    fbk_lines.append(f"AD VA\t{point_id}\t{next_row_hv[1]}\t{next_row_sd[3]}\t{next_row_hv[2]}\t{description}\n")

        return fbk_lines

    with open(input_path, 'r') as infile:
        lines = infile.readlines()

    data = [parse_line(line) for line in lines if line.strip()]
    fbk_lines = create_fbk_nts(data)

    with open(output_path, 'w') as outfile:
        outfile.writelines(fbk_lines)

    print(f"Archivo FBK generado en: {output_path}")


# Función para procesar archivos South_362_66
def process_south_362_66(input_path, output_path):
    try:
        with open(input_path, 'r') as infile:
            lines = infile.readlines()

        data = []
        for line in lines:
            line = line.replace("     ", ",")
            data.append(line.strip().split(","))

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as outfile:
            for i, row in enumerate(data):
                if len(row) == 0 or len(row[0].strip()) == 0:
                    continue

                if row[0] == "STN":
                    outfile.write(f"STN\t{row[1]}\t{row[2]}\n")
                elif row[0] == "BS":
                    outfile.write(f"BS\t{row[1]}\n")
                    outfile.write(f"PRISM\t{row[2]}\n")
                elif row[0] == "SS":
                    if i + 1 < len(data) and len(data[i+1]) >= 4 and data[i+1][0] == "SD":
                        outfile.write(f"AD VA\t{row[1]}\t{data[i+1][1]}\t{data[i+1][3]}\t{data[i+1][2]}\t{row[3]}\n")
                    else:
                        print(f"Warning: Incomplete data for SS at line {i+1 + 1}: {row}")
                        outfile.write(f"AD VA\t{row[1]}\tINCOMPLETE\tINCOMPLETE\tINCOMPLETE\t{row[3]}\n")

    except FileNotFoundError:
        print(f"Error: File not found: {input_path}")
    except IndexError as e:
        print(f"Error: Data format issue - {e}")
    except Exception as e:
        print(f"Error: {e}")

    print(f"Archivo FBK generado en: {output_path}")


# Función para procesar archivos South_362_33
def process_south_362_33(input_path, output_path):
    def clean_lines(input_file):
        with open(input_file, 'r') as infile:
            lines = infile.readlines()
        cleaned_lines = [line[1:-6].strip() for line in lines if len(line) > 6]
        return ''.join(cleaned_lines)

    def parse_fbk(cleaned_data):
        results = []
        stn_pattern = r"_'([^_]+)_\(.*?\)([0-9\.]+)_\+(\d+)_"
        stn_matches = list(re.finditer(stn_pattern, cleaned_data))

        if not stn_matches:
            print("No STN blocks found in the input file. Please verify the input format.")
            return results

        blocks = []
        processed_ad_indices = set()

        for i, match in enumerate(stn_matches):
            stn = match.group(1)
            stn_height = match.group(2)
            bs = match.group(3)

            block_start = match.end()
            block_end = stn_matches[i + 1].start() if i + 1 < len(stn_matches) else len(cleaned_data)
            block_content = cleaned_data[block_start:block_end].strip()

            prism_match = re.search(r",([0-9\.]+)_", block_content)
            prism = prism_match.group(1) if prism_match else None

            ad_pattern = r",([0-9\.]+)_\+(\d+)_ \?\+([0-9]+)m([0-9]+)\+([0-9]+)d\+([\-0-9]+)\*.*?\*([A-Za-z0-9]*)"
            ad_matches = list(re.finditer(ad_pattern, block_content))
            ad_values = []
            for ad_match in ad_matches:
                ad_index = ad_match.group(2)
                if ad_index in processed_ad_indices:
                    continue
                processed_ad_indices.add(ad_index)
                second_val = float(ad_match.group(5)) / 10000
                third_val = float(ad_match.group(3)) / 1000
                fourth_val = float(ad_match.group(4)) / 10000
                fifth_val = ad_match.group(7)
                ad_values.append(
                    f"AD VA\t{ad_index}\t{second_val:.4f}\t{third_val:.3f}\t{fourth_val:.4f}\t{fifth_val}"
                )

            block = {
                "STN": stn,
                "STN_HEIGHT": stn_height,
                "BS": bs,
                "PRISM": prism,
                "AD": ad_values
            }
            blocks.append(block)

        if stn_matches:
            last_block_start = stn_matches[-1].end()
            remaining_content = cleaned_data[last_block_start:].strip()
            ad_pattern_incomplete = r",([0-9\.]+)_\+(\d+).*?\+([0-9]+)m([0-9]+)\+([0-9]+)d.*?\*([A-Za-z0-9]*)"
            ad_matches = list(re.finditer(ad_pattern, remaining_content)) + list(re.finditer(ad_pattern_incomplete, remaining_content))
            for ad_match in ad_matches:
                ad_index = ad_match.group(2)
                if ad_index in processed_ad_indices:
                    continue
                processed_ad_indices.add(ad_index)
                second_val = float(ad_match.group(5)) / 10000
                third_val = float(ad_match.group(3)) / 1000
                fourth_val = float(ad_match.group(4)) / 10000
                fifth_val = ad_match.group(6) if len(ad_match.groups()) >= 6 else ""
                if "AD" not in blocks[-1]:
                    blocks[-1]["AD"] = []
                blocks[-1]["AD"].append(
                    f"AD VA\t{ad_index}\t{second_val:.4f}\t{third_val:.3f}\t{fourth_val:.4f}\t{fifth_val}"
                )

        for block in blocks:
            results.append(f"STN\t{block['STN']}\t{block['STN_HEIGHT']}")
            results.append(f"BS\t{block['BS']}")
            if block["PRISM"]:
                results.append(f"PRISM\t{block['PRISM']}")
            results.extend(block["AD"])

        return results

    cleaned_data = clean_lines(input_path)
    fbk_lines = parse_fbk(cleaned_data)

    if not fbk_lines:
        print("No valid data extracted.")
        return

    with open(output_path, 'w') as outfile:
        outfile.write("\n".join(fbk_lines))

    print(f"Archivo FBK generado en: {output_path}")

# Función para procesar datos con método específico
def process_data(input_file, method, output_file):
    methods = {
        "Geomax.GSI": process_geomax_gsi,
        "Sanding.GSI": process_sanding_gsi,
        "South_362_33": process_south_362_33,
        "South_362_66": process_south_362_66,
        "South_345": process_south_345,
    }

    if method not in methods:
        raise ValueError(f"Unsupported method: {method}")

    methods[method](input_file, output_file)



