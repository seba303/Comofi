# Comofi

Comofi es una herramienta para la conciliación automática de movimientos financieros entre dos fuentes de datos, normalmente:

- extracto bancario
- registro interno o contable

La aplicación compara ambos conjuntos, detecta coincidencias, discrepancias, duplicados y movimientos pendientes, y guarda un historial de cada revisión para su análisis posterior.

## ¿Qué resuelve?

Cuando un equipo financiero o operativo compara dos CSV manualmente, el proceso suele ser lento, repetitivo y propenso a errores. Comofi automatiza esa tarea y ayuda a identificar rápidamente:

- operaciones coincidentes
- diferencias de importe
- diferencias de fecha
- movimientos duplicados
- pendientes por conciliar

## Valor del proyecto

Este proyecto combina tres elementos importantes:

- automatización real de procesos de control financiero
- uso de Python y análisis de datos con pandas
- interfaz web simple y útil para demostrar la funcionalidad en una presentación

Es un buen ejemplo de una aplicación práctica con impacto directo en operaciones bancarias o contables.

## Funcionalidades principales

- carga y validación de CSV con cabeceras esperadas
- normalización de fechas y importes
- emparejamiento exacto por referencia
- emparejamiento aproximado por importe y concepto
- detección de duplicados por origen
- listado de pendientes de conciliación
- historial persistente en SQLite
- exportación de resultados a CSV
- interfaz web para uso local

## Flujo de trabajo

```text
CSV bancario + CSV interno
          ↓
      validación
          ↓
  normalización de datos
          ↓
   emparejamiento / clasificación
          ↓
       historial + exportación
          ↓
    resumen visual y CSV resultante
```

## Demo de salida

```text
=== Resumen de conciliación ===
coincidentes             10
discrepancias             2
duplicados                4
pendientes_banco          2
pendientes_interno        1
```

## Estructura del proyecto

```text
comofi/
  __init__.py
  config.py
  csv_loader.py
  reconciler.py
  history.py
  exporter.py
  samples.py
  web.py

templates/
  base.html
  index.html
  revision.html

data/
  sample_files/
  resultados/
  comofi.db

main.py
requirements.txt
README.md
Dockerfile
```

## Requisitos

- Python 3.10+
- pip
- acceso local para ejecutar la app web

## Instalación

```bash
git clone https://github.com/seba303/Comofi.git
cd Comofi
python -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso rápido

### 1. Generar datos de ejemplo

```bash
python main.py generar-ejemplos
```

### 2. Conciliar dos CSV

```bash
python main.py conciliar data/sample_files/movimientos_bancarios.csv data/sample_files/registros_internos.csv
```

### 3. Ver historial

```bash
python main.py historial
```

### 4. Iniciar interfaz web

```bash
python main.py web
```

La app queda disponible en:

```text
http://127.0.0.1:5000
```

## Formato esperado de los CSV

### Banco

```csv
fecha,referencia,concepto,importe
03/03/2026,TRX-1003,Alquiler oficina marzo,-1200,00
```

### Registro interno

```csv
fecha,id_operacion,detalle,importe
03/03/2026,OP-1003,Alquiler oficina,-1200,50
```

Se aceptan fechas en formatos como:

- dd/mm/yyyy
- yyyy-mm-dd
- dd-mm-yyyy

Y importes en formatos europeos o estándar, por ejemplo:

- 1.234,56
- 1234.56

## Cómo funciona la conciliación

El motor de reglas realiza dos pasos:

1. Emparejamiento exacto por referencia
2. Emparejamiento aproximado por importe y concepto dentro de una ventana de fechas

Después clasifica cada caso en:

- coincidentes
- discrepancias
- duplicados
- pendientes

Todos los umbrales están centralizados en `comofi/config.py` para facilitar ajustes.

## Historial y exportación

Cada ejecución guarda su resultado en SQLite. Además, los resultados se exportan como CSV en la carpeta:

```text
data/resultados/
```

Se generan:

- consolidado completo
- CSV por categoría

## Arquitectura técnica

```text
+------------------+      +-------------------+
| CSV bancario     |      | CSV interno       |
+--------+---------+      +---------+---------+
         |                            |
         v                            v
   csv_loader.py             csv_loader.py
         |                            |
         +-----------+----------------+
                     v
             reconciler.py
                     |
                     v
             result classification
                     |
          +----------+-----------+
          |                      |
          v                      v
    history.py            exporter.py
          |                      |
          +-----------+----------+
                      v
               SQLite + CSV export
```

## Mejoras recomendadas para una presentación

Este proyecto ya tiene una base sólida, pero para una demo profesional se recomienda:

- mejorar la UI de la web con dashboard y métricas
- añadir tests para validación de lógica
- documentar mejor el flujo de negocio
- preparar despliegue con Docker
- mejorar mensajes de error y UX

## Ejecutar con Docker

```bash
docker build -t comofi .
docker run -p 5000:5000 comofi
```

## Licencia

Consulta el archivo `LICENSE` del repositorio para más información.

## Autor

Sebastián Romero

## Estado del proyecto

Proyecto funcional, orientado a la conciliación financiera y listo para ser presentado como demostración de automatización de procesos y análisis de datos.

---

Si quieres, puedes usar este repositorio como base para una presentación técnica de:

- automatización de procesos operativos
- control financiero
- análisis de discrepancias
- generación de reportes y trazabilidad
