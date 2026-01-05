import json
import os
import re
import sys
from mitmproxy import http
from datetime import datetime

STATE_DIR = "/var/lib/c64u-server-switcher"
STATE_FILE = f"{STATE_DIR}/clients.json"

def log(msg):
    """Print with flush for immediate output"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def request(flow: http.HTTPFlow) -> None:
    client_ip = flow.client_conn.peername[0]

    # Get Client-Id header to detect device type
    client_id_header = flow.request.headers.get("Client-Id")

    # Debug: log all incoming requests
    log(f"REQUEST: {flow.request.method} {flow.request.path}")
    log(f"  Client-IP: {client_ip}")
    log(f"  Client-Id: {client_id_header}")
    log(f"  Query params: {dict(flow.request.query)}")
    log(f"  Headers: {dict(flow.request.headers)}")

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
        log(f"  Default server for {client_id_header}: {server_choice}")

    # Check for server parameter in query (from menu selection)
    server_param = flow.request.query.get("server", "").lower()
    if server_param in ["assembly64", "commoserve"]:
        state[client_ip] = server_param
        save_state(state)
        server_choice = server_param
        log(f"SWITCH (menu): {client_ip} -> {server_param}")
        # Remove the server param so it doesn't confuse the real server
        del flow.request.query["server"]

    # Check for server selection in query (from injected menu)
    # Query comes as: (server:assembly64) or (server:commoserve)
    # May also include other search params like (name:"bubble")
    query_string = flow.request.query.get("query", "")
    query_lower = query_string.lower()
    name_string = flow.request.query.get("name", "").lower()
    search_text = query_lower + " " + name_string

    # Handle server menu selection - strip server: from query and continue
    if "server:assembly64" in query_lower or "server:commoserve" in query_lower:
        if "server:assembly64" in query_lower:
            new_server = "assembly64"
        else:
            new_server = "commoserve"

        state[client_ip] = new_server
        save_state(state)
        server_choice = new_server
        log(f"SWITCH (menu): {client_ip} -> {new_server}")

        # Remove server:xxx from query string (case insensitive)
        # Also handle the & operator that joins query parts
        cleaned_query = re.sub(r'\s*&\s*\(server:(assembly64|commoserve)\)', '', query_string, flags=re.IGNORECASE)
        cleaned_query = re.sub(r'\(server:(assembly64|commoserve)\)\s*&\s*', '', cleaned_query, flags=re.IGNORECASE)
        cleaned_query = re.sub(r'\(server:(assembly64|commoserve)\)', '', cleaned_query, flags=re.IGNORECASE)
        # Clean up any leftover empty parens or double spaces
        cleaned_query = cleaned_query.strip()

        # If query is now empty or just whitespace, return confirmation
        if not cleaned_query or cleaned_query == "()":
            flow.response = http.Response.make(
                200,
                json.dumps([{"name": f"Switched to {new_server.upper()}", "id": "0", "category": 0}]),
                {"Content-Type": "application/json"}
            )
            log(f"  No other search params, returning confirmation")
            return
        else:
            # Update query with server part removed and continue with search
            flow.request.query["query"] = cleaned_query
            log(f"  Cleaned query: {cleaned_query}")

    # Also check for keywords in search query (legacy method)
    if "assembly64" in search_text:
        state[client_ip] = "assembly64"
        save_state(state)
        server_choice = "assembly64"
        log(f"SWITCH (keyword): {client_ip} -> Assembly64")

    elif "commoserve" in search_text:
        state[client_ip] = "commoserve"
        save_state(state)
        server_choice = "commoserve"
        log(f"SWITCH (keyword): {client_ip} -> Commoserve")

    # Help feature
    elif "help" in search_text:
        device = "Ultimate64" if client_id_header == "Ultimate" else "C64U"
        help_text = (
            "PROXY HELP:\n"
            f"Device: {device}\n"
            f"Current: {server_choice}\n"
            "Use Server menu or search 'commoserve'/'assembly64' to switch."
        )
        flow.response = http.Response.make(
            200,
            json.dumps({"results": [{"name": help_text}]}),
            {"Content-Type": "application/json"}
        )
        log(f"HELP: Sent help response to {client_ip}")
        return

    # Block requests for our fake info items (id "0" or "info")
    # These are the "Switched to..." or "Currently browsing..." messages
    if re.match(r'/leet/search/entries/(0|info)/', flow.request.path):
        log(f"BLOCKED: Request for info item, returning empty")
        flow.response = http.Response.make(
            200,
            json.dumps([]),
            {"Content-Type": "application/json"}
        )
        return

    # Bot protection
    if not client_id_header and "/leet/search/" not in flow.request.path:
        log(f"BLOCKED: No Client-Id header from {client_ip}")
        flow.kill()
        return

    # Apply header patch
    # C64U (Commodore) accessing assembly64 -> patch to Ultimate
    # Ultimate64 (Ultimate) accessing commoserve -> patch to Commodore
    original_client_id = client_id_header

    # Always fetch presets with Ultimate header to get full Assembly64 menu
    if flow.request.path == "/leet/search/aql/presets":
        if client_id_header != "Ultimate":
            flow.request.headers["Client-Id"] = "Ultimate"
            log(f"PATCHED: {client_ip} Client-Id: {client_id_header} -> Ultimate (fetching full menu)")
        else:
            log(f"FORWARDED: {client_ip} presets request (already Ultimate)")
    elif client_id_header == "Commodore" and server_choice == "assembly64":
        flow.request.headers["Client-Id"] = "Ultimate"
        log(f"PATCHED: {client_ip} Client-Id: Commodore -> Ultimate (accessing Assembly64)")
    elif client_id_header == "Ultimate" and server_choice == "commoserve":
        flow.request.headers["Client-Id"] = "Commodore"
        log(f"PATCHED: {client_ip} Client-Id: Ultimate -> Commodore (accessing Commoserve)")
    else:
        device = "Ultimate64" if client_id_header == "Ultimate" else "C64U"
        log(f"FORWARDED: {client_ip} ({device}) -> {server_choice} (no patch needed)")

    # Forwarding
    flow.request.host = "185.187.254.229"
    flow.request.port = 80
    flow.request.headers["Host"] = "hackerswithstyle.se"
    log(f"  Forwarding to: {flow.request.host}:{flow.request.port}")

def response(flow: http.HTTPFlow) -> None:
    """Intercept responses and inject Server menu option into presets"""
    client_ip = flow.client_conn.peername[0]

    # Debug: log all responses
    log(f"RESPONSE: {flow.request.path}")
    log(f"  Status: {flow.response.status_code}")
    log(f"  Content-Type: {flow.response.headers.get('Content-Type', 'unknown')}")
    log(f"  Content length: {len(flow.response.content)} bytes")

    # Show first 500 chars of response for debugging
    try:
        content_preview = flow.response.content.decode('utf-8')[:500]
        log(f"  Content preview: {content_preview}")
    except:
        log(f"  Content preview: (binary data)")

    # Inject "Currently browsing..." info item into search results
    # Match /leet/search/aql but not /leet/search/aql/presets
    if flow.request.path.startswith("/leet/search/aql") and not flow.request.path.startswith("/leet/search/aql/"):
        log(f"SEARCH RESULTS: Intercepted search response for path: {flow.request.path}")
        try:
            data = json.loads(flow.response.content)
            log(f"  Response type: {type(data).__name__}")

            # Get current server choice for this client
            state = load_state()
            client_id_header = flow.request.headers.get("Client-Id")
            server_choice = state.get(client_ip)

            # Default based on device type
            if server_choice is None:
                if client_id_header == "Ultimate":
                    server_choice = "commoserve"
                else:
                    server_choice = "assembly64"

            # Create info item showing current server
            server_display = "Assembly64" if server_choice == "assembly64" else "Commoserve"
            info_item = {
                "name": f"Browsing: {server_display}",
                "id": "info",
                "category": 0
            }

            # Handle both array and dict responses
            if isinstance(data, list):
                log(f"  Original results count: {len(data)}")
                data.insert(0, info_item)
                log(f"  After injection: {len(data)} items")
            elif isinstance(data, dict) and "results" in data:
                log(f"  Original results count: {len(data['results'])}")
                data["results"].insert(0, info_item)
                log(f"  After injection: {len(data['results'])} items")
            else:
                log(f"  Unknown response format, skipping injection")
                return

            # Update response
            new_content = json.dumps(data)
            flow.response.content = new_content.encode()
            log(f"INJECTED: Info item into search results")
        except json.JSONDecodeError as e:
            log(f"ERROR: JSON decode failed for search results: {e}")
        except Exception as e:
            log(f"ERROR: Search results injection failed: {type(e).__name__}: {e}")

    if flow.request.path == "/leet/search/aql/presets":
        log(f"PRESETS: Intercepted presets response")
        try:
            # Parse the original response
            data = json.loads(flow.response.content)
            log(f"  Original presets count: {len(data)}")

            # Get current server choice for this client
            state = load_state()
            client_id_header = flow.request.headers.get("Client-Id")
            server_choice = state.get(client_ip)

            # Default based on device type
            if server_choice is None:
                if client_id_header == "Ultimate":
                    server_choice = "commoserve"
                else:
                    server_choice = "assembly64"

            # Build server menu with current selection marked with asterisk
            if server_choice == "assembly64":
                server_menu = {
                    "type": "server",
                    "description": "Server",
                    "values": [
                        {"aqlKey": "assembly64", "name": "* Assembly64"},
                        {"aqlKey": "commoserve", "name": "Commoserve"}
                    ]
                }
            else:
                server_menu = {
                    "type": "server",
                    "description": "Server",
                    "values": [
                        {"aqlKey": "commoserve", "name": "* Commoserve"},
                        {"aqlKey": "assembly64", "name": "Assembly64"}
                    ]
                }

            # Inject Server menu at the beginning
            data.insert(0, server_menu)
            log(f"  After injection: {len(data)} items (current: {server_choice})")

            # Update response
            new_content = json.dumps(data)
            flow.response.content = new_content.encode()
            log(f"INJECTED: Server menu into presets response")
            log(f"  New content length: {len(new_content)}")
        except json.JSONDecodeError as e:
            log(f"ERROR: JSON decode failed: {e}")
            log(f"  Raw content: {flow.response.content[:200]}")
        except AttributeError as e:
            log(f"ERROR: Attribute error: {e}")
        except Exception as e:
            log(f"ERROR: Unexpected error: {type(e).__name__}: {e}")
