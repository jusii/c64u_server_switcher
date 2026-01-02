# c64u_server_switcher
DNS and mitmproxy hack to allow user to use both assembly64 and commoserve servers for games and apps.

# Usage
to run it mitmdump -p 80 -s  --mode reverse:http://185.187.254.229:80 --set block_global=false

And then you need your DNS to return your servers IP address when C64U queries for hackerswithstyle.se

Added feature so you can switch straight from C64U UI between commoserver and assembly64. Default is to access assembly64 but if you want to switch to commoserve side do a search and in Name: field put commoserve and to switch back to assembly, search once for assembly64

Server will keep track of the IP requests come and remembers your settings between searches.
