$TTL 300

@ IN SOA ns1.sentinelhub.com. admin.sentinelhub.com. (
    2026102301
    3600
    900
    604800
    300
)

@       IN NS    ns1.sentinelhub.com.

@       IN A     192.168.0.4
ns1     IN A     192.168.0.4
grafana IN A     192.168.0.4
cctv    IN A     192.168.0.4
