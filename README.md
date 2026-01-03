# C64U Server Switcher

DNS and mitmproxy hack to allow the new Commodore 64 Ultimate to access both Assembly64 and Commoserve sections of the server.

## How it works

The new Commodore 64 Ultimate (C64U) shares the same motherboard as the Ultimate 64 but comes with its own official Commoserve server section, also hosted on `hackerswithstyle.se`. By default, the C64U only accesses the Commoserve section.

The device makes HTTP requests using simple HTTP/1.1 protocol with headers like `User-Agent: Assembly Query` and `Client-Id: Commodore`.

This tool intercepts those requests by:

1. **DNS override** - Configure your local DNS to resolve `hackerswithstyle.se` to your proxy server's IP instead of the real server
2. **Reverse proxy** - mitmproxy runs in reverse mode, receiving the C64U's requests and forwarding them to either Assembly64 or Commoserve backend
3. **Server switching** - The proxy inspects search queries and switches backends based on magic keywords

This allows the Commodore 64 Ultimate to access the full Assembly64 game library without modifying firmware.

## Requirements

- mitmproxy
- dnsmasq

## Installation

### 1. Install dependencies

```bash
sudo apt install mitmproxy dnsmasq
```

### 2. Install the script

```bash
sudo mkdir -p /usr/local/lib/c64u-server-switcher
sudo cp c64u_server_switcher.py /usr/local/lib/c64u-server-switcher/
```

### 3. Install the systemd service

```bash
sudo cp c64u-server-switcher.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable c64u-server-switcher
sudo systemctl start c64u-server-switcher
```

### 4. Configure DNS

Use the provided `dnsmasq.conf` to spoof `hackerswithstyle.se` to your server's IP address.

On Ubuntu/Debian systems, systemd-resolved conflicts with dnsmasq (both try to bind port 53). Fix this by pointing resolv.conf to use systemd-resolved's upstream config:

```bash
sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
sudo systemctl restart systemd-resolved
```

Then configure your C64U to use your server as its DNS server.

## Usage

### Switching between servers

You can switch between Commoserve and Assembly64 directly from the C64U UI:

| To access...   | Search for...  |
|----------------|----------------|
| Assembly64     | `assembly64`   |
| Commoserve     | `commoserve`   |

The server remembers your preference per IP address between searches.

**Default:** Assembly64

### Manual run (for testing)

```bash
mitmdump -p 80 -s c64u_server_switcher.py --mode reverse:http://185.187.254.229:80 --set block_global=false
```

### Service management

```bash
# Check status
sudo systemctl status c64u-server-switcher

# View logs
sudo journalctl -u c64u-server-switcher -f

# Restart
sudo systemctl restart c64u-server-switcher
```

## Example packet capture

```
0000   0c ea 14 42 02 6f 10 20 ba 0d 1b d4 81 00 00 02   ...B.o. ........
0010   08 00 45 00 00 cc 00 45 00 00 ff 06 3f 5d c0 a8   ..E....E....?]..
0020   02 40 b9 bb fe e5 cc d0 00 50 00 00 19 c1 76 e5   .@.......P....v.
0030   e6 3f 50 18 1c 84 cc 6b 00 00 47 45 54 20 2f 6c   .?P....k..GET /l
0040   65 65 74 2f 73 65 61 72 63 68 2f 61 71 6c 2f 70   eet/search/aql/p
0050   72 65 73 65 74 73 20 48 54 54 50 2f 31 2e 31 0d   resets HTTP/1.1.
0060   0a 41 63 63 65 70 74 2d 65 6e 63 6f 64 69 6e 67   .Accept-encoding
0070   3a 20 69 64 65 6e 74 69 74 79 0d 0a 48 6f 73 74   : identity..Host
0080   3a 20 68 61 63 6b 65 72 73 77 69 74 68 73 74 79   : hackerswithsty
0090   6c 65 2e 73 65 0d 0a 55 73 65 72 2d 41 67 65 6e   le.se..User-Agen
00a0   74 3a 20 41 73 73 65 6d 62 6c 79 20 51 75 65 72   t: Assembly Quer
00b0   79 0d 0a 43 6c 69 65 6e 74 2d 49 64 3a 20 43 6f   y..Client-Id: Co
00c0   6d 6d 6f 64 6f 72 65 0d 0a 43 6f 6e 6e 65 63 74   mmodore..Connect
00d0   69 6f 6e 3a 20 63 6c 6f 73 65 0d 0a 0d 0a         ion: close....
```
