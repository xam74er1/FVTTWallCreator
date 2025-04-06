import json
import os
from time import sleep

import websocket
from rel import rel

from prepare_wall_packet import send_packet_from_json, packet_from_scene

time_recive = False
lqst_message_num = "0"
message_list = []
waite_responce = True

default_param = {
    "json_path": "C:/Users/xam74/PycharmProjects/AventOfCode2021/randomTest/fvtt/ply_wall.json",
    "scene_id": "01hWoyt47nejpWxo",
    "orignialimage_path": "C:/Users/xam74/Downloads/kokotovillage.png",
    "scale_dim_x": 3640 * 1.33,
    "scale_dim_y": 5460 * 1.33,
    "scene_name": "test scene 2"
}


def on_message(ws, message):
    if "userActivity" in message:
        return
    print(f"Received: {message}")
    global time_recive
    global lqst_message_num
    global message_list
    global waite_responce

    try:

        expected_number = lqst_message_num
        print(f"Expected number: {expected_number}")
        recive_number = message[2:].split("[")[0]
        print(f"Recive number: {recive_number}")
        if recive_number == expected_number:
            time_recive = True
            print("size of the list", len(message_list))

            if waite_responce:
                to_send = message_list.pop(0)
                send(ws, to_send)
            else:
                for msg in message_list:
                    send(ws, msg)
            print("Time recive")
        else:
            try:
                print("debut message ", message[3:100])
                decoded_message = json.loads(message[3:])[0]
                scenes = decoded_message.get("scenes", [])
                wahnted_scenes = None
                for scene in scenes:
                    if scene.get("name") == default_param["scene_name"]:
                        wahnted_scenes = scene
                        break
                if wahnted_scenes:
                    try:
                        all_packet = packet_from_scene(default_param["json_path"], default_param["orignialimage_path"],
                                                       wahnted_scenes
                                                       , default_param["scale_dim_x"],
                                                       default_param["scale_dim_y"])
                        for carac in all_packet:
                            dump_data = ["modifyDocument", carac]
                            dup = json.dumps(dump_data, ensure_ascii=False)
                            send(ws, dup)
                    except Exception as e:
                        print(f"Error preparing packet: {e}")
                        print("stack strace", e.__traceback__)
                    finally:
                        print("close connection")
                        ws.close()
                        rel.stop()



            except Exception as e:
                print(f"Error get world info and send packetge: {e}")
                return
    except Exception as e:
        print(f"Error: {e}")
        print("Time not recive")


def on_error(ws, error):
    print(f"Error: {error}")


def on_close(ws, close_status_code, close_msg):
    print("Connection closed", close_status_code, close_msg)
    exit(1)


OP_CODE = 42
counter = 0


def send(ws, message, code=OP_CODE):
    global counter
    global lqst_message_num
    sleep(0.01)
    if code == OP_CODE:
        message = f"{code}{counter}{message}"
        lqst_message_num = str(counter)
        counter += 1
    print("send", message)
    ws.send(message)


def on_open(ws):
    global message_list
    print("Connection established")
    print(ws)
    send(ws, "40", 0)
    send(ws, "[\"world\"]", )
    send(ws, "[\"time\"]")

    character_data = send_packet_from_json(**default_param)

    print("size of the list B", len(message_list))


def connect_to_foundry(session):
    # WebSocket URL
    ip = os.getenv('IP')
    url = f"ws://{ip}/socket.io/?session={session}&EIO=4&transport=websocket"

    # Headers from your curl command
    headers = {
        "Origin": f"http://{ip}",
        "Cache-Control": "no-cache",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7,ru;q=0.6,sv;q=0.5",
        "Pragma": "no-cache",
        "Cookie": f"session={session}",
        "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }

    # Create WebSocket connection
    ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # Start the connection
    print("before run forever")
    ws.run_forever(dispatcher=rel)
    rel.signal(2, rel.abort)
    print("before dispatch")
    rel.dispatch()
    print("after dispatch")


def load_env():
    # Load environment variables from .env file
    with open('.env', 'r') as f:
        for line in f:
            key, value = line.strip().split('=')

            os.environ[key.upper()] = value


def send_token(session, image_path, data, scene_name, scale_dim_x=1, scale_dim_y=1):
    # Load environment variables from .env file
    load_env()
    if not session:
        session = os.getenv('SESSION')
    default_param["json_path"] = data
    default_param["scene_id"] = scene_name
    default_param["orignialimage_path"] = image_path
    default_param["scale_dim_x"] = scale_dim_x
    default_param["scale_dim_y"] = scale_dim_y
    # Connect to Foundry
    connect_to_foundry(session)


if __name__ == "__main__":
    # Enable debug output
    # websocket.enableTrace(True)

    # Start the connection
    load_env()
    session = os.getenv('SESSION')
    connect_to_foundry(session)

# Convert the format
