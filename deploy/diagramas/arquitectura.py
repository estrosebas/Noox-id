"""Arquitectura lógica de NooxID, dibujada como código con mingrammer/diagrams.

    uv run --with diagrams python arquitectura.py      # requiere Graphviz (dot) en el PATH

Genera arquitectura.png y arquitectura.svg en esta carpeta.
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.generic.compute import Rack
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server
from diagrams.onprem.database import MySQL
from diagrams.programming.framework import Flask, React
from diagrams.programming.language import JavaScript, Python

GRAFICO = {"fontsize": "22", "fontname": "Helvetica", "pad": "0.4", "nodesep": "0.55", "ranksep": "1.0", "labelloc": "t"}
NODO = {"fontname": "Helvetica", "fontsize": "13"}
ARISTA = {"fontname": "Helvetica", "fontsize": "11"}

for formato in ("png", "svg"):
    with Diagram("Arquitectura lógica de NooxID", filename="arquitectura", outformat=formato, show=False,
                 direction="LR", graph_attr=GRAFICO, node_attr=NODO, edge_attr=ARISTA):
        empleados = Users("Empleados")

        with Cluster("Navegador del empleado"):
            panel = React("Panel de NooxID\n(React 19 + Vite)")
            sdk = JavaScript("SDK de captura\nMediaPipe BlazeFace")

        with Cluster("Aplicaciones empresariales"):
            apps = [Rack("CRM"), Rack("ERP"), Rack("App a medida")]

        with Cluster("NooxID · API (Flask)"):
            api = Flask("API REST")
            with Cluster("Servicios"):
                rostro = Python("Rostro\nYuNet + SFace (OpenCV)")
                factores = [Python("TOTP (RFC 6238)"), Python("Código por correo")]
                permisos = Python("Roles y permisos")

        base = MySQL("MySQL\nusuarios, apps, vectores,\nroles")
        smtp = Server("Servidor SMTP")

        empleados >> Edge(label="usa") >> panel
        empleados >> Edge(label="usa") >> apps
        panel >> Edge(label="JWT") >> api
        apps >> Edge(label="X-API-Key\n+ X-App-ID", color="firebrick") >> api
        api >> Edge(label="sirve /sdk", style="dashed", color="steelblue") >> sdk
        api >> rostro
        api >> factores
        api >> permisos
        [rostro, permisos] >> base
        factores[1] >> Edge(label="SMTP") >> smtp
