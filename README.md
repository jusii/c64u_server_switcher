# C64U Server Switcher

Access **both** Assembly64 and Commoserve from your C64 Ultimate or Ultimate64!

## What is this?

The C64 Ultimate and Ultimate64 each only access one server by default:
- **C64 Ultimate** → Commoserve only
- **Ultimate64** → Assembly64 only

This proxy lets you access **both servers** from either device by using a dropdown menu in the search interface.

## What you need

- A Linux computer (Raspberry Pi works great) that stays on while you use your C64
- Basic comfort with Linux terminal commands

## Quick Start

### Step 1: Download the files

On your Linux computer, open a terminal and run:

```bash
git clone https://github.com/YOUR_USERNAME/c64u_server_switcher.git
cd c64u_server_switcher
```

### Step 2: Install required software

```bash
sudo apt update
sudo apt install mitmproxy dnsmasq
```

### Step 3: Install the proxy

Copy these commands one at a time:

```bash
sudo mkdir -p /usr/local/lib/c64u-server-switcher
sudo mkdir -p /var/lib/c64u-server-switcher
sudo cp c64u_server_switcher.py /usr/local/lib/c64u-server-switcher/
sudo cp c64u-server-switcher.service /etc/systemd/system/
```

### Step 4: Start the proxy

```bash
sudo systemctl daemon-reload
sudo systemctl enable c64u-server-switcher
sudo systemctl start c64u-server-switcher
```

To verify it's running:

```bash
sudo systemctl status c64u-server-switcher
```

You should see "active (running)" in green.

### Step 5: Set up DNS redirect

Your C64 needs to think your Linux computer *is* the game server. Choose ONE option:

#### Option A: Router DNS override (easiest if your router supports it)

1. Log into your router's admin page (usually http://192.168.1.1)
2. Look for "DNS settings", "DNS override", or "custom DNS entries"
3. Add an entry: `hackerswithstyle.se` → `[your Linux computer's IP]`
4. Your C64 can use DHCP normally - no changes needed on the device

#### Option B: Use the included DNS server

If your router doesn't support DNS overrides:

1. Edit `dnsmasq.conf` and change `192.168.1.100` to your Linux computer's IP address, then copy it:
   ```bash
   nano dnsmasq.conf
   sudo cp dnsmasq.conf /etc/dnsmasq.d/c64u-server-switcher.conf
   ```

2. Edit `/etc/systemd/resolved.conf` and add this line:
   ```
   DNSStubListener=no
   ```

3. Run these commands:
   ```bash
   sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
   sudo systemctl restart systemd-resolved
   sudo systemctl enable dnsmasq
   sudo systemctl start dnsmasq
   ```

4. On your C64, go to network settings and configure a static IP:
   - **Use DHCP**: Disabled
   - **Static IP**: Pick an unused IP on your network (e.g., 192.168.2.64)
   - **Static Netmask**: 255.255.255.0
   - **Static Gateway**: Your router's IP (e.g., 192.168.2.1)
   - **Static DNS**: Your Linux computer's IP address (e.g., 192.168.2.100)

   Note: You need a static IP because you can't set a custom DNS server when using DHCP on the C64.

### Step 6: Test it!

1. Turn on your C64 Ultimate or Ultimate64
2. Go to Remote mode and open the search menu
3. You should see a **Server** dropdown at the top!
4. Select Assembly64 or Commoserve and search for something

## How to use

### Switching servers

Use the **Server** dropdown in the search menu to switch between Assembly64 and Commoserve.

Alternatively, type `assembly64` or `commoserve` in the Name field and search.

### How do I know which server I'm on?

Every search result shows "Browsing: Assembly64" or "Browsing: Commoserve" as the first item.

### Defaults

The proxy gives you access to what you *can't* normally access:
- **C64 Ultimate** → defaults to Assembly64
- **Ultimate64** → defaults to Commoserve

Your server choice is remembered between searches.

## Troubleshooting

### Proxy not running?

```bash
sudo systemctl status c64u-server-switcher
sudo journalctl -u c64u-server-switcher -f
```

### Can't connect from C64?

1. Make sure your Linux computer's IP hasn't changed
2. Verify DNS is working: from another computer, `ping hackerswithstyle.se` should return your Linux computer's IP
3. Check that port 80 isn't blocked by a firewall

### Server dropdown not showing?

The C64 caches the menu when entering Remote mode. Try rebooting your C64 or re-entering the Remote menu.

## Technical details

<details>
<summary>Click to expand</summary>

### How it works

The C64 Ultimate sends `Client-Id: Commodore` and gets Commoserve. The Ultimate64 sends `Client-Id: Ultimate` and gets Assembly64. This proxy intercepts requests and changes the `Client-Id` header to access the other server.

### Architecture

1. **DNS override** - `hackerswithstyle.se` resolves to your proxy instead of the real server
2. **Reverse proxy** - mitmproxy receives requests and forwards them to the real server
3. **Header patching** - The proxy changes `Client-Id` based on your server selection
4. **Menu injection** - A "Server" dropdown is injected into the search menu

### Manual run (for testing)

```bash
mitmdump -p 80 -s c64u_server_switcher.py --mode reverse:http://185.187.254.229:80 --set block_global=false
```

### Service management

```bash
sudo systemctl status c64u-server-switcher   # Check status
sudo journalctl -u c64u-server-switcher -f   # View logs
sudo systemctl restart c64u-server-switcher  # Restart
```

</details>

## Changelog

- Added "Browsing: {server}" indicator as first search result
- Always return full Assembly64 menu (more options) regardless of current server
- Added Server dropdown menu - switch servers directly from the UI
- Added Ultimate64 support - both devices can access both servers
- Smart defaults: each device defaults to the server it can't normally access
- Server preference is remembered per IP address
