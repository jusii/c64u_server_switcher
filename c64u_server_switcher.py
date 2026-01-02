
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
    
    state = load_state()
    # CHANGE: Default is now "Ultimate" for new users
    current_choice = state.get(client_ip, "Ultimate") 

    query_string = flow.request.query.get("query", "").lower()

    # 1. KEYWORD LOGIC
    if "assembly64" in query_string:
        state[client_ip] = "Ultimate"
        save_state(state)
        current_choice = "Ultimate"
        print(f"[{timestamp}] SWITCH: {client_ip} -> Assembly64 (Ultimate)")
    
    elif "commoserve" in query_string:
        state[client_ip] = "Commodore"
        save_state(state)
        current_choice = "Commodore"
        print(f"[{timestamp}] SWITCH: {client_ip} -> CommoServe (Commodore)")

    # 2. HELP FEATURE
    elif "help" in query_string:
        help_text = (
            "PROXY HELP:\n"
            "Default: Assembly64 (Full Repo)\n"
            "Search 'commoserve' to downgrade repo.\n"
            "Search 'assembly64' to restore full repo."
        )
        flow.response = http.Response.make(
            200, 
            json.dumps({"results": [{"name": help_text}]}), 
            {"Content-Type": "application/json"}
        )
        return

    # 3. BOT PROTECTION
    client_id_header = flow.request.headers.get("Client-Id")
    if not client_id_header and "/leet/search/" not in flow.request.path:
        flow.kill() 
        return

    # 4. APPLY HEADER PATCH
    # If the C64 identifies as "Commodore" but our state says "Ultimate", we swap.
    if client_id_header == "Commodore" and current_choice == "Ultimate":
        flow.request.headers["Client-Id"] = "Ultimate"
        print(f"[{timestamp}] PATCHED: {client_ip} using Assembly64 (DEFAULT)")
    else:
        print(f"[{timestamp}] FORWARDED: {client_ip} using {current_choice}")

    # 5. FORWARDING
    flow.request.host = "185.187.254.229"
    flow.request.port = 80
    flow.request.headers["Host"] = "hackerswithstyle.se"
