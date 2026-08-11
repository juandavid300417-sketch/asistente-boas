"""
ASISTENTE PARA BOAS V4 — interfaz Streamlit.

El programa SOLO RECOMIENDA. La actualizacion del documento historico es manual.

Toda la logica vive en boas_core.py. Este archivo solo arma la pantalla.
"""

import io

import pandas as pd
import streamlit as st

import boas_core as bc

st.set_page_config(page_title="Asistente para BOAS V4", page_icon="📄",
                   layout="wide")

# --------------------------------------------------------------------------
# Encabezado
# --------------------------------------------------------------------------

st.title("Asistente para BOAS V4")
st.caption("Recomienda la clasificacion de pagos comparando los textos del FBL3N "
           "contra las plantillas del Glosario BOAS de cada pais. "
           "**El programa solo recomienda:** la actualizacion del documento "
           "historico es manual.")

with st.expander("Como funciona el motor"):
    st.markdown("""
Cada plantilla del glosario se compone de dos tipos de contenido:

| En la plantilla | Trato del programa |
|---|---|
| Numeros, letras, `/`, `-`, `:`, espacios | **Ancla**: obligatorio, se compara literal y en orden |
| `*`, `(NUMERO)`, `?` | **Variable**: cualquier contenido, de cualquier largo (o ninguno) |

Dos capas conviven:

1. **Anclas** — se verifican sobre el **texto crudo**. Es la unica capa que puede
   distinguir dos categorias que solo difieren en unos digitos internos.
2. **Similitud** — se calcula sobre el **texto normalizado**. Como la normalizacion
   borra los bloques de digitos, es ciega al digito discriminador y por eso
   **nunca llega a recomendacion directa** (techo de 84 puntos).

Si al menos una plantilla ancla, solo compiten las que anclaron.

**Regla para escribir plantillas:** antes de poner un asterisco sobre un digito,
preguntate si ese numero es distinto cuando cambias de categoria pero siempre igual
dentro de la misma. Si es asi, es un **ancla** y va escrito literal, nunca dentro de
un comodin.
    """)

# --------------------------------------------------------------------------
# Carga de archivos
# --------------------------------------------------------------------------

st.header("1. Cargar archivos")
c1, c2 = st.columns(2)
with c1:
    f_fbl3n = st.file_uploader("FBL3N (export SAP, .xlsx)", type=["xlsx", "xls"])
with c2:
    f_glos = st.file_uploader("Glosario BOAS (.xlsx)", type=["xlsx", "xls"])

if not f_fbl3n or not f_glos:
    st.info("Sube los dos archivos para continuar. "
            "Ninguno se guarda: se procesan en memoria y se descartan al cerrar.")
    st.stop()

try:
    fbl3n = bc.cargar_fbl3n(f_fbl3n)
except Exception as e:
    st.error(f"No se pudo leer el FBL3N: {e}")
    st.stop()

try:
    glosarios = bc.cargar_glosario(f_glos)
except Exception as e:
    st.error(f"No se pudo leer el glosario: {e}")
    st.stop()

# --------------------------------------------------------------------------
# Depuracion
# --------------------------------------------------------------------------

datos, info = bc.depurar(fbl3n)

if datos.empty:
    st.error("Despues de eliminar las filas sin texto no queda ninguna fila que procesar.")
    st.stop()

st.header("2. Depuracion")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Filas originales", info["n_original"])
m2.metric("Eliminadas (texto en blanco)", info["n_vacias"])
m3.metric("Filas en proceso", info["n_proceso"])
m4.metric("Textos unicos", info["textos_unicos"])

if info["sin_mapeo"]:
    st.warning(f"Company codes sin mapeo a pais: {info['sin_mapeo']} "
               f"({info['n_sin_mapeo']} filas). Se procesan como SIN MAPEO "
               f"y van a revision manual.")

paises = sorted(datos["pais"].unique())
faltan_hoja = [p for p in paises if not bc.hoja_valida(glosarios, p)]
if faltan_hoja:
    st.warning(f"Sin hoja valida en el glosario: {faltan_hoja}. "
               f"Esas filas van a revision manual.")

# --------------------------------------------------------------------------
# Procesamiento
# --------------------------------------------------------------------------

with st.spinner("Clasificando..."):
    res, detalle = bc.procesar(datos, glosarios)
    final = bc.tabla_final(res)

st.header("3. Metricas por banda")
st.dataframe(bc.metricas(res), use_container_width=True, hide_index=True)

with st.expander("Detalle por pais (plantillas activas y textos unicos)"):
    st.dataframe(detalle, use_container_width=True, hide_index=True)

st.caption("Recomendacion directa solo se alcanza por anclas. La similitud tiene "
           "techo de 84 puntos, asi que por si sola nunca recomienda directo.")

# --------------------------------------------------------------------------
# Auditoria del glosario
# --------------------------------------------------------------------------

st.header("4. Auditoria del glosario")
st.caption("Control de calidad de las plantillas. Sirve para saber donde escribir "
           "las siguientes.")

pais_aud = st.selectbox("Pais a auditar", paises)
aud = bc.auditar_pais(datos, glosarios, pais_aud)

if aud is None:
    st.info(f"No hay hoja de glosario valida para {pais_aud}.")
else:
    a1, a2, a3 = st.columns(3)
    a1.metric("Plantillas activas", aud["n_plantillas"])
    a2.metric("Cobertura por anclas", f"{aud['cobertura_pct']}%",
              help=f"{aud['cobertura_filas']} de {aud['n_filas']} filas")
    a3.metric("Textos unicos", aud["n_textos"])

    if not aud["sin_match"].empty:
        st.subheader(f"{len(aud['sin_match'])} plantillas sin match en este archivo")
        st.caption("Puede ser un error de escritura **o** que esa categoria no salio "
                   "esta vez. Verificar en los datos antes de corregir.")
        st.dataframe(aud["sin_match"], use_container_width=True, hide_index=True)

    if not aud["genericas"].empty:
        st.subheader(f"{len(aud['genericas'])} plantillas demasiado genericas")
        st.caption("Tocan mas del 60% de los textos: probablemente les faltan anclas "
                   "propias de su categoria.")
        st.dataframe(aud["genericas"], use_container_width=True, hide_index=True)

    if not aud["conflictos"].empty:
        st.subheader(f"{len(aud['conflictos'])} conflictos")
        st.caption("Dos CONCEPT distintos matchean el mismo texto con la misma "
                   "especificidad. Alguna tiene el digito discriminador tapado por "
                   "un asterisco.")
        st.dataframe(aud["conflictos"], use_container_width=True, hide_index=True)

    if not aud["descubiertos"].empty:
        st.subheader("Textos sin cubrir, ordenados por volumen")
        st.caption("Esta es la cola de trabajo priorizada para escribir plantillas nuevas.")
        st.dataframe(aud["descubiertos"].head(30), use_container_width=True,
                     hide_index=True)

# --------------------------------------------------------------------------
# Resultado y descarga
# --------------------------------------------------------------------------

st.header("5. Resultado")

bandas = ["(todas)"] + sorted(final["banda"].unique().tolist())
f1, f2 = st.columns(2)
filtro_pais = f1.selectbox("Filtrar por pais", ["(todos)"] + paises)
filtro_banda = f2.selectbox("Filtrar por banda", bandas)

vista = final
if filtro_pais != "(todos)":
    vista = vista[vista["pais"] == filtro_pais]
if filtro_banda != "(todas)":
    vista = vista[vista["banda"] == filtro_banda]

st.dataframe(vista, use_container_width=True, hide_index=True)
st.caption(f"Mostrando {len(vista)} de {len(final)} filas.")

buffer = bc.exportar_excel(final, io.BytesIO())
st.download_button(
    "Descargar RECOMENDACION_BOAS.xlsx",
    data=buffer.getvalue(),
    file_name="RECOMENDACION_BOAS.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
)
st.caption("El Excel incluye todas las filas, sin los filtros de arriba.")
