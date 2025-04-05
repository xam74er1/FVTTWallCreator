import json
import os
from time import sleep

import websocket
from rel import rel

from prepare_wall_packet import send_packet_from_json

time_recive = False
lqst_message_num = "0"
message_list = []

def on_message(ws, message):
    if "userActivity" in message:
        return
    print(f"Received: {message}")
    global time_recive
    global lqst_message_num
    global message_list

    try:

        expected_number = lqst_message_num
        print(f"Expected number: {expected_number}")
        recive_number = message[2:].split("[")[0]
        print(f"Recive number: {recive_number}")
        if recive_number == expected_number:
            time_recive = True
            print("size of the list", len(message_list))

            to_send = message_list.pop(0)
            send(ws, to_send)
            print("Time recive")
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
    send(ws, "[\"time\"]")

    #temporary
    json_path = "C:/Users/xam74/PycharmProjects/AventOfCode2021/randomTest/fvtt/ply_wall.json"
    scene_id = "01hWoyt47nejpWxo"
    orignialimage_path = "C:/Users/xam74/Downloads/kokotovillage.png"
    map_dim_x = 3640
    map_dim_y = 5460
    character_data = send_packet_from_json(json_path, scene_id,orignialimage_path,map_dim_x,map_dim_y)

    print("size of the list A", len(character_data))
    for carac in character_data:
        dump_data = ["modifyDocument", carac]
        dup = json.dumps(dump_data,ensure_ascii=False)
        send(ws, dup)
        #message_list.append(dup)
    ws.close()

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

if __name__ == "__main__":
    # Enable debug output
    # websocket.enableTrace(True)

    # Start the connection
    load_env()
    session = os.getenv('SESSION')
    connect_to_foundry(session)

# Convert the format
