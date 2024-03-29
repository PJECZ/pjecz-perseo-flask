# pjecz-perseo-flask

Es un sistema web hecho con Flask para administrar la nómina.

## Docker

Ejecutar con contenedores **Docker** en la raíz del proyecto.

```bash
docker-compose up
```

Levantará los servicios de **Flask**, **PostgreSQL** y **Redis**.

Lea el archivo [docker-compose.yml](docker-compose.yml) para más información.

## Requerimientos

Los requerimiento son

- Python 3.11
- PostgreSQL 15
- Redis

## Instalación

Bajar una copia del repositorio

```bash
git clone https://github.com/PJECZ/pjecz-perseo-flask.git
```

Cambiar al directorio del proyecto

```bash
cd pjecz-perseo-flask
```

Crear el entorno virtual

```bash
python3.11 -m venv .venv
```

Ingresar al entorno virtual

```bash
source venv/bin/activate
```

Actualizar el gestor de paquetes **pip**

```bash
pip install --upgrade pip
```

Instalar el paquete **wheel** para compilar las dependencias

```bash
pip install wheel
```

Instalar **poetry** en el entorno virtual si no lo tiene desde el sistema operativo

```bash
pip install poetry
```

Configurar **poetry** para que use el entorno virtual dentro del proyecto

```bash
poetry config virtualenvs.in-project true
```

Instalar las dependencias por medio de **poetry**

```bash
poetry install
```

## Configuración

Crear un archivo `.env` en la raíz del proyecto con las variables, establecer sus propios SECRET_KEY, DB_PASS, CLOUD_STORAGE_DEPOSITO y SALT.

```bash
# Flask
FLASK_APP=perseo.app
FLASK_DEBUG=1
SECRET_KEY=XXXXXXXX

# Database
DB_HOST=127.0.0.1
DB_PORT=8432
DB_NAME=pjecz_perseo
DB_USER=adminpjeczperseo
DB_PASS=XXXXXXXX
SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://adminpjeczperseo:XXXXXXXX@127.0.0.1:8432/pjecz_perseo"

# Google Cloud Storage
CLOUD_STORAGE_DEPOSITO=XXXXXXXX

# Host
HOST=http://localhost:5000

# Redis
REDIS_URL=redis://127.0.0.1:6379
TASK_QUEUE=pjecz_perseo

# RRHH Personal API
RRHH_PERSONAL_URL=https://rrhh-personal-api-key.justiciadigital.gob.mx/v4
RRHH_PERSONAL_API_KEY=XXXXXXXX

# Salt sirve para cifrar el ID con HashID
SALT=XXXXXXXX

# Si esta en PRODUCTION se evita reiniciar la base de datos
DEPLOYMENT_ENVIRONMENT=develop

# Directorio donde se encuentran las quincenas y sus respectivos archivos de explotacion
EXPLOTACION_BASE_DIR=/home/guivaloz/Downloads/NOMINAS
```

Crear un archivo `.bashrc` que se ejecute al iniciar la terminal

```bash
if [ -f ~/.bashrc ]
then
    . ~/.bashrc
fi

if command -v figlet &> /dev/null
then
    figlet Perseo Flask
else
    echo "== Perseo Flask"
fi
echo

if [ -f .env ]
then
    echo "-- Variables de entorno"
    export $(grep -v '^#' .env | xargs)
    echo "   CLOUD_STORAGE_DEPOSITO: ${CLOUD_STORAGE_DEPOSITO}"
    echo "   DB_HOST: ${DB_HOST}"
    echo "   DB_PORT: ${DB_PORT}"
    echo "   DB_NAME: ${DB_NAME}"
    echo "   DB_USER: ${DB_USER}"
    echo "   DB_PASS: ${DB_PASS}"
    echo "   DEPLOYMENT_ENVIRONMENT: ${DEPLOYMENT_ENVIRONMENT}"
    echo "   EXPLOTACION_BASE_DIR: ${EXPLOTACION_BASE_DIR}"
    echo "   FLASK_APP: ${FLASK_APP}"
    echo "   HOST: ${HOST}"
    echo "   REDIS_URL: ${REDIS_URL}"
    echo "   RRHH_PERSONAL_URL: ${RRHH_PERSONAL_URL}"
    echo "   RRHH_PERSONAL_API_KEY: ${RRHH_PERSONAL_API_KEY}"
    echo "   SALT: ${SALT}"
    echo "   SECRET_KEY: ${SECRET_KEY}"
    echo "   SQLALCHEMY_DATABASE_URI: ${SQLALCHEMY_DATABASE_URI}"
    echo "   TASK_QUEUE: ${TASK_QUEUE}"
    echo
    export PGHOST=$DB_HOST
    export PGPORT=$DB_PORT
    export PGDATABASE=$DB_NAME
    export PGUSER=$DB_USER
    export PGPASSWORD=$DB_PASS
fi

if [ -d .venv ]
then
    echo "-- Python Virtual Environment"
    source .venv/bin/activate
    echo "   $(python3 --version)"
    export PYTHONPATH=$(pwd)
    echo "   PYTHONPATH: ${PYTHONPATH}"
    echo
    if [ -f cli/app.py ]
    then
        echo "-- Ejecutar el CLI"
        alias cli="python3 ${PWD}/cli/app.py"
        echo "   cli --help"
        echo
        echo "-- Reiniciar la base de datos"
        function reiniciar() {
            CLI="python3 ${PWD}/cli/app.py"
            $CLI db reiniciar \
            && $CLI conceptos alimentar \
            && $CLI bancos alimentar \
            && $CLI tabuladores alimentar
        }
        export -f reiniciar
        echo "   reiniciar"
        echo
        echo "-- Alimentar archivos de explotacion"
        function alimentar() {
            CLI="python3 ${PWD}/cli/app.py"
            CLAVE=$1
            FECHA_DE_PAGO=$2
            $CLI nominas alimentar $CLAVE $FECHA_DE_PAGO \
            && $CLI percepciones_deducciones alimentar $CLAVE \
            && $CLI cuentas alimentar-bancarias $CLAVE \
            && $CLI cuentas alimentar-monederos $CLAVE \
            && $CLI beneficiarios alimentar $CLAVE
        }
        export -f alimentar
        echo "   alimentar <Quincena YYYYMM> <Fecha de pago YYYY-MM-DD>"
        echo
        echo "-- Alimentar Apoyos y Aguinaldos de 2023"
        echo "   cli nominas alimentar-apoyos-anuales 202322 2023-11-17"
        echo "   cli nominas alimentar-aguinaldos 202324 2023-12-05"
        echo
        echo "-- Sincronizar datos con la API de RRHH Personal"
        echo "   cli centros_trabajos sincronizar"
        echo "   cli personas sincronizar"
        echo
        echo "-- Migrar y eliminar RFCs erroneos"
        echo "   cli personas migrar-eliminar-rfc --eliminar <RFCEquivocado> <RFCCorrecto>"
        echo
        echo "-- Eliminar o recuperar Conceptos segun no/si se usen"
        echo "   cli conceptos eliminar-recuperar"
        echo "   cli conceptos eliminar-recuperar --quincena-clave 202320"
        echo
    fi
    echo "-- Arrancar Flask o RQ Worker"
    alias arrancar="flask run --port=5000"
    alias fondear="rq worker ${TASK_QUEUE}"
    echo "   arrancar = flask run --port=5000"
    echo "   fondear = rq worker ${TASK_QUEUE}"
    echo
fi
```

## Cargar las variables de entorno y el entorno virtual

Antes de usar el CLI o de arrancar el servidor de **Flask** debe cargar las variables de entorno y el entorno virtual.

```bash
. .bashrc
```

Tendrá el alias al **CLI**

```bash
cli --help
```

## Reiniciar la base de datos

En `.bashrc` se encuentra la función `reiniciar` que ejecuta el **CLI** para reiniciar la base de datos y alimentarla con los datos iniciales. Siempre que haya los archivos necesarios en el directorio `seed`.

```bash
reiniciar
```

## Recargar archivos de explotacion

Con los archivos de explotacion en el directorio `EXPLOTACION_BASE_DIR` puede recargar los datos de la quincena **202320** con:

```bash
recargar 202320
```

Para recargar todo el año 2023

```bash
for ((i = 202301 ; i < 202322 ; i++ )); do recargar "$i"; done
```

## Generar cada producto

Para crear los archivos XLSX a partir del **CLI** ejecute:

```bash
generar 202320
```

En cambio, esos generadores para el sistema web en **Flask** se ejecutan como tareas en el fondo con **RQ Worker**.

## Tareas en el fondo

Abrir una terminal _Bash_, cargar el `.bashrc` y ejecutar

```bash
fondear
```

Así se ejecutarán las tareas en el fondo con **RQ Worker**.

## Arrancar

Abrir otra terminal _Bash_, cargar el `.bashrc` y ejecutar

```bash
arrancar
```

Así se arrancará el servidor de **Flask**.

## Requirements.txt

Como se usa _poetry_ al cambiar las dependencias debe crear un nuevo `requirements.txt` con:

```bash
poetry export -f requirements.txt --output requirements.txt --without-hashes
```
