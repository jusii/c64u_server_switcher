import json
import os
from mitmproxy import http
from datetime import datetime

STATE_FILE = "clients.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def request(flow: http.HTTPFlow) -> None:
    client_ip = flow.client_conn.peername[0]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get Client-Id header to detect device type
    client_id_header = flow.request.headers.get("Client-Id")

    # Load saved server choice for this client (assembly64 or commoserve)
    state = load_state()
    server_choice = state.get(client_ip)

    # Default: give them what they can't normally access
    # C64U (Commodore) -> default to assembly64
    # Ultimate64 (Ultimate) -> default to commoserve
    if server_choice is None:
        if client_id_header == "Ultimate":
            server_choice = "commoserve"
        else:
            server_choice = "assembly64"

    query_string = flow.request.query.get("query", "").lower()

    # 1. KEYWORD LOGIC
    if "assembly64" in query_string:
        state[client_ip] = "assembly64"
        save_state(state)
        server_choice = "assembly64"
        print(f"[{timestamp}] SWITCH: {client_ip} -> Assembly64")

    elif "commoserve" in query_string:
        state[client_ip] = "commoserve"
        save_state(state)
        server_choice = "commoserve"
        print(f"[{timestamp}] SWITCH: {client_ip} -> Commoserve")

    # 2. HELP FEATURE
    elif "help" in query_string:
        device = "Ultimate64" if client_id_header == "Ultimate" else "C64U"
        help_text = (
            "PROXY HELP:\n"
            f"Device: {device}\n"
            f"Current: {server_choice}\n"
            "Search 'commoserve' or 'assembly64' to switch."
        )
        flow.response = http.Response.make(
            200,
            json.dumps({"results": [{"name": help_text}]}),
            {"Content-Type": "application/json"}
        )
        return

    # 3. BOT PROTECTION
    if not client_id_header and "/leet/search/" not in flow.request.path:
        flow.kill()
        return

    # 4. APPLY HEADER PATCH
    # C64U (Commodore) accessing assembly64 -> patch to Ultimate
    # Ultimate64 (Ultimate) accessing commoserve -> patch to Commodore
    if client_id_header == "Commodore" and server_choice == "assembly64":
        flow.request.headers["Client-Id"] = "Ultimate"
        print(f"[{timestamp}] PATCHED: {client_ip} (C64U) -> Assembly64")
    elif client_id_header == "Ultimate" and server_choice == "commoserve":
        flow.request.headers["Client-Id"] = "Commodore"
        print(f"[{timestamp}] PATCHED: {client_ip} (Ultimate64) -> Commoserve")
    else:
        device = "Ultimate64" if client_id_header == "Ultimate" else "C64U"
        print(f"[{timestamp}] FORWARDED: {client_ip} ({device}) -> {server_choice}")

    # 5. FORWARDING
    flow.request.host = "185.187.254.229"
    flow.request.port = 80
    flow.request.headers["Host"] = "hackerswithstyle.se"
