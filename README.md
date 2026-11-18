# Spotifice

**Spotifice** es una aplicación distribuida de *streaming* de audio desarrollada en
Python sobre el middleware [ZeroC Ice](https://zeroc.com/ice). Es el proyecto
de una práctica cuyo objetivo es aplicar los conceptos teóricos de sistemas
distribuidos y ver cómo cooperan de forma remota distintos componentes para ofrecer
un servicio multimedia.

## Requisitos
Se asume que Pyhton 3 y ZeroC Ice (junto con sus librerías para Python) ya están instalados cumpliendo lo siguiente:

- **Python 3.10 o superior**.
- **ZeroC Ice 3.7.x** (NO 3.8).

Además, se requieren las siguientes dependencias:

| Dependencia | Para qué se usa |
|---|---|
| PyGObject (`gi`) | Acceso a GStreamer desde Python |
| GStreamer (`plugins-base`, `plugins-good`) | Procesado y reproducción de audio |
| mutagen | Lectura de metadatos (tags) de ficheros de audio |
| `make` *(opcional)* | Automatización de tareas de build y test |
| pytest *(opcional)* | Ejecución de tests |
| tmux *(opcional)* | Lanzar los componentes con `demo.sh` |
| wget *(opcional)* | Descargar archivos |

## Instalación (Linux)
Probado sobre Ubuntu 22.04.

```bash
sudo apt update
sudo apt install -y \
    python3-gi \
    gir1.2-gstreamer-1.0 \
    python3-mutagen \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good
```

**Dependencias opcionales** (Makefiles, `demo.sh` y tests):

```bash
sudo apt install -y \
    tmux \
    make \
    wget \
    python3-pytest
```
