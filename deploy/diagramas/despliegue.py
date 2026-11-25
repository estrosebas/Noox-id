"""Despliegue de NooxID en Oracle Cloud (Ampere A1) con HestiaCP, Nginx y Docker, como código (mingrammer/diagrams).

    uv run --with diagrams python despliegue.py        # requiere Graphviz (dot) en el PATH

Genera despliegue.png y despliegue.svg en esta carpeta.
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.generic.compute import Rack
from diagrams.oci.compute import VM
from diagrams.oci.network import InternetGateway, SecurityLists
from diagrams.onprem.certificates import LetsEncrypt
from diagrams.onprem.client import Users
from diagrams.onprem.container import Docker
from diagrams.onprem.database import MariaDB
from diagrams.onprem.network import Gunicorn, Nginx
from diagrams.onprem.compute import Server
from diagrams.programming.framework import Flask, React

GRAFICO = {"fontsize": "22", "fontname": "Helvetica", "pad": "0.4", "nodesep": "0.5", "ranksep": "0.9", "labelloc": "t"}
NODO = {"fontname": "Helvetica", "fontsize": "13"}
ARISTA = {"fontname": "Helvetica", "fontsize": "11"}

for formato in ("png", "svg"):
    with Diagram("Despliegue de NooxID en Oracle Cloud (Ampere A1) con HestiaCP", filename="despliegue",
                 outformat=formato, show=False, direction="LR", graph_attr=GRAFICO, node_attr=NODO, edge_attr=ARISTA):
        empleados = Users("Empleados\n(navegador)")
        apps = Rack("Apps empresariales\n(CRM, ERP)\nservidor con API key")
        le = LetsEncrypt("Let's Encrypt\n(certificado TLS)")

        with Cluster("Oracle Cloud Infrastructure · VCN"):
            puerta = InternetGateway("Internet Gateway")
            lista = SecurityLists("Lista de seguridad\nsolo 80 y 443")

            with Cluster("VM.Standard.A1.Flex · Ampere ARM\n4 OCPU · 20 GB RAM · 200 GB"):
                vm = VM("Ubuntu/Debian aarch64\n+ HestiaCP")

                with Cluster("Nginx de HestiaCP"):
                    http = Nginx("puerto 80\nplantilla .tpl\nredirige a HTTPS")
                    https = Nginx("puerto 443\nplantilla .stpl\nTLS + HSTS")

                with Cluster("Sitio estático\nid.dominio.com"):
                    spa = React("Panel (build de Vite)")

                with Cluster("Docker · solo 127.0.0.1:5000"):
                    api = Flask("NooxID API\n(Flask)")
                    wsgi = Gunicorn("gunicorn\n1 worker + hilos")
                    base = MariaDB("MariaDB\n(red interna)")

        smtp = Server("Servidor SMTP\n(códigos por correo)")

        empleados >> Edge(label="HTTPS 443") >> puerta
        apps >> Edge(label="HTTPS 443\nX-API-Key", color="firebrick") >> puerta
        puerta >> lista >> https
        empleados >> Edge(label="HTTP 80", style="dotted") >> puerta
        puerta >> Edge(style="dotted") >> http
        http >> Edge(label="301", style="dotted") >> https
        https >> Edge(label="archivos\nestáticos") >> spa
        https >> Edge(label="proxy_pass\napi.id.dominio.com", color="steelblue") >> wsgi
        wsgi >> api >> base
        api >> Edge(label="SMTP 587", style="dashed") >> smtp
        le >> Edge(label="ACME", style="dashed") >> https
