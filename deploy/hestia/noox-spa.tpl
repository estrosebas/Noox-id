#=========================================================================#
# noox-spa · plantilla HTTP (puerto 80) para el panel (SPA de Vite)        #
# Redirige a HTTPS salvo la validación ACME. Va con noox-spa.stpl.         #
#=========================================================================#

server {
    listen      %ip%:%web_port%;
    server_name %domain_idn% %alias_idn%;
    access_log  /var/log/%web_system%/domains/%domain%.log combined;
    error_log   /var/log/%web_system%/domains/%domain%.error.log error;

    location ^~ /.well-known/acme-challenge/ {
        root         %docroot%;
        default_type "text/plain";
        try_files    $uri =404;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
