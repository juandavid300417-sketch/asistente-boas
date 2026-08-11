# Asistente para BOAS V4

App web que recomienda la clasificacion de pagos comparando los textos de un reporte
FBL3N (SAP) contra las plantillas del Glosario BOAS del pais correspondiente.

**El programa solo recomienda.** La actualizacion del documento historico es manual.

---

## Archivos del repo

| Archivo | Que hace |
|---|---|
| `app.py` | La interfaz: carga de archivos, metricas, auditoria, descarga |
| `boas_core.py` | El motor: anclas, similitud, clasificacion. No sabe nada de Streamlit |
| `requirements.txt` | Dependencias |
| `.gitignore` | Impide subir archivos de datos al repo por accidente |

La separacion es intencional: `boas_core.py` se puede probar y reutilizar sin levantar
la app, y la logica de negocio no queda mezclada con codigo de interfaz.

---

## Privacidad: que NO va al repo

Este repo es **publico**. Nunca subas:

- Archivos FBL3N (contienen datos de operaciones)
- El archivo del Glosario BOAS
- Cualquier `.xlsx` o `.csv`

El `.gitignore` ya bloquea esas extensiones, pero verificalo antes de cada `push`.

Los archivos que el usuario sube en la app **se procesan en memoria y no se guardan
en ningun lado**. Streamlit Cloud no los persiste.

---

## Como publicarlo (paso a paso)

### 1. Crear el repositorio en GitHub

1. Entra a [github.com](https://github.com) y haz clic en **New repository**.
2. Nombre: `asistente-boas` (o el que prefieras).
3. Visibilidad: **Public** (Streamlit Community Cloud lo requiere en el plan gratis).
4. **No** marques "Add a README" — ya tienes uno.
5. Clic en **Create repository**.

### 2. Subir los archivos

La forma mas simple, sin instalar nada:

1. En el repo recien creado, clic en **Add file → Upload files**.
2. Arrastra los cuatro archivos: `app.py`, `boas_core.py`, `requirements.txt`,
   `.gitignore`.
3. Escribe un mensaje ("version inicial") y clic en **Commit changes**.

Si prefieres linea de comandos:

```bash
git init
git add app.py boas_core.py requirements.txt .gitignore
git commit -m "Version inicial"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/asistente-boas.git
git push -u origin main
```

### 3. Desplegar en Streamlit Cloud

1. Entra a [share.streamlit.io](https://share.streamlit.io) e inicia sesion con tu
   cuenta de GitHub.
2. Clic en **New app** → **Deploy a public app from GitHub**.
3. Completa:
   - **Repository:** `TU_USUARIO/asistente-boas`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Clic en **Deploy**. La primera vez tarda unos minutos instalando dependencias.

Al terminar te da una URL publica (algo como
`https://asistente-boas.streamlit.app`) que puedes compartir con el equipo.

### 4. Actualizar la app

Cada vez que hagas `commit` a la rama `main`, Streamlit Cloud redespliega solo.
No hay que hacer nada mas.

---

## Correrlo en tu maquina (sin nube)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abre en `http://localhost:8501`.

---

## Como funciona el motor

Cada plantilla del glosario se compone de dos tipos de contenido:

| En la plantilla | Trato del programa |
|---|---|
| Numeros, letras, `/`, `-`, `:`, espacios | **Ancla**: obligatorio, se compara literal y en orden |
| `*`, `(NUMERO)`, `?` | **Variable**: cualquier contenido, de cualquier largo (o ninguno) |

Dos capas conviven:

1. **Anclas** — se verifican sobre el **texto crudo**. Es la unica capa capaz de
   distinguir dos categorias que solo difieren en unos digitos internos.
2. **Similitud** — se calcula sobre el **texto normalizado**. Como la normalizacion
   borra los bloques de digitos, es ciega al digito discriminador y por eso **nunca
   llega a recomendacion directa** (techo de 84 puntos).

Si al menos una plantilla ancla, solo compiten las que anclaron y gana la mas
especifica. La similitud queda apagada.

### Bandas de confianza

| Puntaje | Banda | Que devuelve |
|---|---|---|
| ≥ 85 | Recomendacion directa | CONCEPT + ACTION |
| 60 – 85 | Revisar candidatos | Solo CONCEPT |
| < 60 | Revision manual | Nada |

Solo se llega a recomendacion directa por anclas.

### Depuracion

Las filas con `Text` en blanco **se eliminan** al inicio y no aparecen en ninguna
etapa posterior. Las filas con texto pero con un company code sin mapeo si se
procesan: quedan marcadas como `SIN MAPEO` y van a revision manual.

---

## Como escribir plantillas

La calidad del resultado depende casi por completo de como esten escritas las
plantillas del glosario, no del codigo.

> Antes de poner un asterisco sobre un digito, preguntate: *este numero es distinto
> cuando cambio de categoria, pero siempre igual dentro de la misma categoria?*
> Si la respuesta es si, es un **ancla**: va escrito literal, nunca dentro de un
> comodin. Si cambia linea por linea aunque sea del mismo grupo, es **variable**:
> va como `*`.

El error mas costoso es meter el digito discriminador dentro de un asterisco: el
programa pierde la unica senal que le permite separar dos categorias parecidas.

**Metodo recomendado:** no escribas la plantilla a mano. Copia y pega un texto real
y reemplaza sobre el los tramos que cambian por `*`. Asi los ceros y los separadores
quedan exactos.

Ver la *Guia de Plantillas del Glosario BOAS* para el metodo completo y los errores
frecuentes.

---

## Auditoria del glosario

La app incluye una auditoria por pais que reporta:

- **Plantillas sin match en este archivo** — puede ser error de escritura **o** que
  esa categoria simplemente no salio esta vez. Verificar en los datos antes de
  corregir.
- **Plantillas demasiado genericas** — tocan mas del 60% de los textos.
- **Conflictos** — dos CONCEPT distintos matchean el mismo texto con la misma
  especificidad.
- **Textos sin cubrir ordenados por volumen** — la cola de trabajo priorizada para
  escribir plantillas nuevas.

Para montar un pais nuevo no hay que tocar codigo: se corre la app, se mira la lista
de textos sin cubrir y se escriben plantillas en el glosario empezando por las de
mayor volumen.
