# bank-marketing-dataops

Este proyecto contiene la base técnica e infraestructura automatizada utilizando la metodología **DataOps** para la **Evaluación Parcial N°2** de la asignatura **Gestión de Datos para IA (ITY1101)** en Duoc UC.

## ¿De qué trata el proyecto?
El objetivo es procesar el **Bank Marketing Dataset (Caso de Estudio 2)** para optimizar las campañas de marketing de depósitos a plazo de un banco. El código hace pasar los datos de forma automatizada por las 4 etapas exigidas en la pauta:

* **Ingesta (`ingestion/`):** Se encarga de la recepción y lectura del archivo original desde la carpeta `data/raw/`.
* **Limpieza (`processing/`):** Realiza la limpieza, transformación y casteo de las variables del banco.
* **Validación (`validation/`):** Aplica las reglas estructurales y semánticas mediante esquemas para evitar anomalías.
* **Carga (`loading/`):** Realiza la carga y persistencia de los datos finales en su destino (Supabase / PostgreSQL).

Todo el flujo se orquesta y ejecuta en orden secuencial desde el archivo central `src/main.py`.

---

## Configuración del Entorno (Paso a Paso)

Sigue estos comandos estrictamente en tu terminal para configurar el repositorio de forma local:

### 1. Ingresar a la carpeta raíz del proyecto
```bash
cd bank_marketing_dataops

```

### 2. Configurar Poetry de forma local

```bash
poetry config virtualenvs.in-project true

```

### 3. Instalar dependencias del proyecto

```bash
poetry install

```

### 4. Crear el archivo de configuración (.env)

```bash
cp .env.example .env

```

---

## Cómo Probar la Infraestructura y los Tests

Para verificar que las rutas dinámicas, el sistema de registros y la suite de pruebas quedaron bien conectados, ejecuta el orquestador principal desde la raíz:

```bash
poetry run python -m src.main

```

Al ejecutarlo se crearán automáticamente las carpetas locales (`data/processed/` y `logs/`) y nacerá el archivo de bitácora diario, el cual sirve como la **evidencia técnica de ejecución sin errores** requerida para el informe.

Para correr las pruebas locales automatizadas (Pytest) que también evalúa GitHub Actions, ejecuta:

```bash
poetry run pytest

```
