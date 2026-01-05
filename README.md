# C64U Server Switcher

DNS and mitmproxy hack to allow Commodore 64 Ultimate and Ultimate64 devices to access both Assembly64 and Commoserve sections of the server.

## Supported devices

| Device | Native Client-Id | Native server | This proxy gives access to |
|--------|------------------|---------------|----------------------------|
| Commodore 64 Ultimate (C64U) | Commodore | Commoserve | Assembly64 |
| Ultimate64 | Ultimate | Assembly64 | Commoserve |

## How it works

The Commodore 64 Ultimate (C64U) and Ultimate64 share the same motherboard but access different sections of `hackerswithstyle.se` based on their `Client-Id` header:

- **C64U** sends `Client-Id: Commodore` → accesses Commoserve
- **Ultimate64** sends `Client-Id: Ultimate` → accesses Assembly64

This tool intercepts requests and patches the `Client-Id` header to access the other server:

1. **DNS override** - Configure your local DNS to resolve `hackerswithstyle.se` to your proxy server's IP
2. **Reverse proxy** - mitmproxy receives requests and forwards them to the real server
3. **Header patching** - The proxy changes `Client-Id` based on which server you want to access
4. **Server switching** - Search for magic keywords to switch between servers

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
sudo mkdir -p /var/lib/c64u-server-switcher
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

You need to make `hackerswithstyle.se` resolve to your proxy server's IP. Two options:

**Option A: Use your router/existing DNS server (recommended)**

Add a DNS override for `hackerswithstyle.se` pointing to your proxy server's IP in your router or Pi-hole/AdGuard/etc. This way your C64U can use DHCP normally.

**Option B: Use dnsmasq on the proxy server**

Use the provided `dnsmasq.conf` to run DNS on the same server as the proxy.

On Ubuntu/Debian systems, systemd-resolved conflicts with dnsmasq (both try to bind port 53). Fix this:

1. Disable the DNS stub listener by adding `DNSStubListener=no` to `/etc/systemd/resolved.conf`
2. Update the resolv.conf symlink:

```bash
sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
sudo systemctl restart systemd-resolved
```

With this option, configure your C64U with a static IP and set DNS to your Linux server's IP.

## Usage

### Switching between servers

There are two ways to switch between servers:

**Method 1: Server dropdown menu**

The proxy injects a "Server" dropdown into the search menu. Select Assembly64 or Commoserve from the dropdown and submit your search.

**Method 2: Magic keywords**

Type `assembly64` or `commoserve` in the Name field and search.

| To access...   | Search for...  |
|----------------|----------------|
| Assembly64     | `assembly64`   |
| Commoserve     | `commoserve`   |

The server remembers your preference per IP address between searches.

**Defaults** (gives you what you can't normally access):
- C64U → Assembly64
- Ultimate64 → Commoserve

### Server indicator

Search results always show "Browsing: Assembly64" or "Browsing: Commoserve" as the first item so you know which server you're currently using.

### Limitations

The device caches the search menu when entering Remote mode. The `*` indicator in the Server dropdown shows the boot-time server, not the currently selected one. To update the menu indicator, reboot the device or re-enter the Remote menu.

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

## Changelog

- Added "Browsing: {server}" indicator as first search result
- Always return full Assembly64 menu (more options) regardless of current server
- Added Server dropdown menu - switch servers directly from the UI without magic keywords
- Added Ultimate64 support - now both C64U and Ultimate64 can access both servers
- Smart defaults: each device now defaults to the server it can't normally access
- Server preference is remembered per IP address
