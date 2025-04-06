import json

import cv2


def load_file(path):
    try:
        with open(path, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return None


def load_polygon_lines(json_file, min_distance=5,proportion_x=1, proportion_y=1):
    lines = []
    print("json file keys", json_file.keys())
    for polygon in json_file.get("polygons", {}):
        merged_points = []
        for point in polygon:
            if not merged_points:
                merged_points.append(point)
            else:
                last_point = merged_points[-1]
                distance = ((point[0] - last_point[0]) ** 2 + (point[1] - last_point[1]) ** 2) ** 0.5
                if distance > min_distance:
                    merged_points.append(point)
        for i in range(len(merged_points)):
            x1, y1 = merged_points[i]
            x2, y2 = merged_points[(i + 1) % len(merged_points)]
            line = [[x1*proportion_x, y1*proportion_y], [x2*proportion_x, y2*proportion_y]]
            lines.append(line)
    print("prepqre lines")
    for line in json_file.get("lines", []):
        x1, y1 , x2, y2 = line
        line = [[x1*proportion_x, y1*proportion_y], [x2*proportion_x, y2*proportion_y]]
        lines.append(line)
    print("number of lines", len(lines))
    return lines


def prepare_packet(json_file,scnene_id,proportion_x=1, proportion_y=1):
    all_messages = []
    min_distance = 20
    lines = load_polygon_lines(json_file,min_distance,proportion_x, proportion_y)
    min_x = min([line[0][0] for line in lines])
    min_y = min([line[0][1] for line in lines])
    max_x = max([line[1][0] for line in lines])
    max_y = max([line[1][1] for line in lines])
    for i in range(5):
        print(f"Line {i}: {lines[i]}")  # Print the first 5 lines for debugging
    for line in lines:
        message = {"type": "Wall", "action": "create", "operation": {"data": [
            {"light": 20,
             "sight": 20,
             "sound": 20,
             "move": 20,
             "c": [line[0][0], line[0][1] , line[1][0], line[1][1]],
             "_id": None, "dir": 0,
             "door": 0,
             "ds": 0,
             "threshold": {"light": None, "sight": None, "sound": None, "attenuation": False},
             "flags": {}}],
            "modifiedTime": 1743865107186,
            "render": True,
            "renderSheet": False,
            "parentUuid":
                "Scene."+scnene_id,}}
        all_messages.append(message)
    return all_messages

def get_image_proportion(orignialimage_path,map_dim_x,map_dim_y):
    # Load the original image
    image = cv2.imread(orignialimage_path)
    if image is None:
        raise ValueError(f"Image at {orignialimage_path} not found or cannot be loaded.")

    # Get the dimensions of the original image
    original_height, original_width = image.shape[:2]

    # Calculate the proportions
    proportion_x = map_dim_x / original_width
    proportion_y = map_dim_y / original_height

    return proportion_x, proportion_y

def send_packet_from_json(wall_data, scene_id, orignialimage_path=None, map_dim_x=None, map_dim_y=None):

    proportion_x, proportion_y = 1, 1
    if orignialimage_path and map_dim_x and map_dim_y:
        proportion_x, proportion_y = get_image_proportion(orignialimage_path,map_dim_x,map_dim_y)

    json_file = None
    if isinstance(wall_data, str):
        print(f"Loading JSON file from {wall_data}")
        json_file = load_file(wall_data)
    elif isinstance(wall_data, dict):
        print("Loading JSON data from dictionary")
        json_file = wall_data
    if json_file is None:
        print("Failed to load JSON file.")
        raise ValueError("Invalid JSON data provided.")
    all_messages = prepare_packet(json_file,scene_id,proportion_x, proportion_y)
    return all_messages

def packet_from_scene(wall_data,original_image,scene,scale_x,scale_y):
    scene_id = scene.get("_id")
    width = scene.get("width")*scale_x
    height = scene.get("height")*scale_y
    return send_packet_from_json(wall_data, scene_id, original_image, width, height)




if __name__ == "__main__":
    json_path = "C:/Users/xam74/PycharmProjects/AventOfCode2021/randomTest/fvtt/ply_wall.json"
    scene_id = "12345"
    orignialimage_path = "C:/Users/xam74/Downloads/kokotovillage.png"
    map_dim_x = 3640
    map_dim_y = 5460
    messages = send_packet_from_json(json_path, scene_id,orignialimage_path,map_dim_x,map_dim_y)