#=========================================================================#
# noox-proxy · plantilla HTTP (puerto 80) para HestiaCP                    #
# Todo lo que llega por HTTP se redirige a HTTPS, salvo la validación ACME #
# de Let's Encrypt. Va junto con noox-proxy.stpl (mismo nombre).           #
#=========================================================================#

server {
    listen      %ip%:%web_port%;
    server_name %domain_idn% %alias_idn%;
    access_log  /var/log/%web_system%/domains/%domain%.log combined;
    error_log   /var/log/%web_system%/domains/%domain%.error.log error;

    # Hestia valida el dominio con HTTP-01 desde el docroot: este camino no se redirige
    location ^~ /.well-known/acme-challenge/ {
        root         %docroot%;
        default_type "text/plain";
        try_files    $uri =404;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
