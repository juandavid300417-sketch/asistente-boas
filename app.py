"""
ASISTENTE PARA BOAS — interfaz Streamlit.

El programa SOLO RECOMIENDA. La actualizacion del documento historico es manual.

La logica vive en boas_core.py y el estilo en estilos.py. Este archivo solo
arma la pantalla.
"""

import io

import streamlit as st

import boas_core as bc
import estilos as es

st.set_page_config(page_title="Asistente para BOAS",
                   page_icon="◧",
                   layout="wide",
                   initial_sidebar_state="expanded")

st.markdown(es.CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Barra lateral: carga de archivos
# --------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Archivos")
    f_fbl3n = st.file_uploader("FBL3N (export SAP)", type=["xlsx", "xls"])
    f_glos = st.file_uploader("Glosario BOAS", type=["xlsx", "xls"])
    st.markdown(es.nota("Los archivos se procesan en memoria y no se guardan "
                        "en ningun servidor."), unsafe_allow_html=True)

    with st.expander("Como se decide"):
        st.markdown("""
**Anclas** — lo que escribes literal en la plantilla. Se verifican sobre el
texto crudo. Es la unica capa capaz de separar dos categorias que solo
difieren en unos digitos internos.

**Similitud** — se calcula sobre el texto normalizado, donde los bloques de
digitos ya fueron borrados. Es ciega al digito discriminador, asi que **por si
sola nunca recomienda directo**: su techo son 84 puntos.

Si alguna plantilla ancla, solo compiten las que anclaron.
        """)

st.markdown(es.cabecera(), unsafe_allow_html=True)

if not f_fbl3n or not f_glos:
    st.markdown(es.nota("Carga el FBL3N y el glosario en el panel izquierdo "
                        "para empezar."), unsafe_allow_html=True)
    st.stop()

# --------------------------------------------------------------------------
# Carga y depuracion
# --------------------------------------------------------------------------

try:
    fbl3n = bc.cargar_fbl3n(f_fbl3n)
except Exception as e:
    st.error(f"No se pudo leer el FBL3N. {e}")
    st.stop()

try:
    glosarios = bc.cargar_glosario(f_glos)
except Exception as e:
    st.error(f"No se pudo leer el glosario. {e}")
    st.stop()

datos, info = bc.depurar(fbl3n)

if datos.empty:
    st.error("Despues de eliminar las filas sin texto no queda nada que procesar.")
    st.stop()

with st.spinner("Clasificando..."):
    res, detalle = bc.procesar(datos, glosarios)
    final = bc.tabla_final(res)

# --------------------------------------------------------------------------
# Escalera de confianza: lo primero que se ve
# --------------------------------------------------------------------------

conteos = final["banda"].value_counts().to_dict()
st.markdown(es.escalera(conteos, len(final)), unsafe_allow_html=True)

via_ancla = int((res["via"] == "ancla").sum())
st.markdown(es.nota(
    f"Solo se llega a recomendacion directa por anclas: "
    f"<strong>{via_ancla:,}</strong> de {len(res):,} filas anclaron contra una "
    f"plantilla. El resto se resolvio por similitud, que no puede firmar."
), unsafe_allow_html=True)

st.markdown(es.fichas([
    ("Filas del archivo", f"{info['n_original']:,}", False),
    ("Eliminadas sin texto", f"{info['n_vacias']:,}", True),
    ("En proceso", f"{info['n_proceso']:,}", False),
    ("Textos unicos", f"{info['textos_unicos']:,}", False),
]), unsafe_allow_html=True)

paises = sorted(datos["pais"].unique())
avisos = []
if info["sin_mapeo"]:
    avisos.append(f"Company codes sin pais: {', '.join(info['sin_mapeo'])} "
                  f"({info['n_sin_mapeo']} filas van a revision manual).")
faltan_hoja = [p for p in paises if not bc.hoja_valida(glosarios, p)]
if faltan_hoja:
    avisos.append(f"Sin hoja en el glosario: {', '.join(faltan_hoja)}.")
if avisos:
    st.markdown(es.nota(" ".join(avisos), alerta=True), unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Pestanas
# --------------------------------------------------------------------------

t_res, t_aud, t_diag = st.tabs(["Resultado", "Auditoria del glosario",
                                "Diagnostico"])

with t_res:
    c1, c2 = st.columns(2)
    f_pais = c1.selectbox("Pais", ["Todos"] + paises)
    f_banda = c2.selectbox("Banda", ["Todas"] + sorted(final["banda"].unique()))

    vista = final
    if f_pais != "Todos":
        vista = vista[vista["pais"] == f_pais]
    if f_banda != "Todas":
        vista = vista[vista["banda"] == f_banda]

    st.dataframe(vista, use_container_width=True, hide_index=True, height=460)
    st.caption(f"{len(vista):,} de {len(final):,} filas")

    buffer = bc.exportar_excel(final, io.BytesIO())
    st.download_button("Descargar Excel completo",
                       data=buffer.getvalue(),
                       file_name="RECOMENDACION_BOAS.xlsx",
                       mime=("application/vnd.openxmlformats-officedocument"
                             ".spreadsheetml.sheet"),
                       type="primary")
    st.caption("El Excel trae todas las filas, sin los filtros de arriba.")

with t_aud:
    pais_aud = st.selectbox("Pais a auditar", paises, key="aud")
    aud = bc.auditar_pais(datos, glosarios, pais_aud)

    if aud is None:
        st.markdown(es.nota(f"No hay hoja de glosario para {pais_aud}."),
                    unsafe_allow_html=True)
    else:
        st.markdown(es.fichas([
            ("Plantillas activas", aud["n_plantillas"], False),
            ("Cobertura por anclas", f"{aud['cobertura_pct']}%", False),
            ("Filas cubiertas", f"{aud['cobertura_filas']:,}", False),
            ("Textos unicos", f"{aud['n_textos']:,}", False),
        ]), unsafe_allow_html=True)

        if not aud["descubiertos"].empty:
            st.markdown("## Sin cubrir, por volumen")
            st.markdown(es.nota("La cola de trabajo priorizada: la plantilla que "
                                "mas rinde escribir es la de arriba."),
                        unsafe_allow_html=True)
            st.dataframe(aud["descubiertos"].head(25),
                         use_container_width=True, hide_index=True)

        if not aud["sin_match"].empty:
            st.markdown("## Plantillas sin match en este archivo")
            st.markdown(es.nota("Puede ser un error de escritura <strong>o</strong> "
                                "que esa categoria no aparecio esta vez. "
                                "Verificar en los datos antes de corregir nada."),
                        unsafe_allow_html=True)
            st.dataframe(aud["sin_match"], use_container_width=True,
                         hide_index=True)

        if not aud["genericas"].empty:
            st.markdown("## Plantillas demasiado genericas")
            st.markdown(es.nota("Tocan mas del 60% de los textos: les faltan "
                                "anclas propias de su categoria."),
                        unsafe_allow_html=True)
            st.dataframe(aud["genericas"], use_container_width=True,
                         hide_index=True)

        if not aud["conflictos"].empty:
            st.markdown("## Conflictos")
            st.markdown(es.nota("Dos CONCEPT distintos matchean el mismo texto con "
                                "la misma especificidad: alguna tiene el digito "
                                "discriminador tapado por un asterisco."),
                        unsafe_allow_html=True)
            st.dataframe(aud["conflictos"], use_container_width=True,
                         hide_index=True)

with t_diag:
    st.markdown("## Metricas por pais")
    st.dataframe(bc.metricas(res), use_container_width=True, hide_index=True)

    st.markdown("## Glosario cargado")
    st.dataframe(detalle, use_container_width=True, hide_index=True)

    pais_d = st.selectbox("Pais", paises, key="diag")
    insp = bc.inspeccionar(datos, pais_d)

    st.markdown("## Textos mas repetidos")
    st.dataframe(insp["top"], use_container_width=True, hide_index=True)

    st.markdown("## Formatos estructurales")
    st.markdown(es.nota("Cada corrida de digitos se colapsa a <code>D</code> y "
                        "cada corrida de letras a <code>A</code>. Sirve para ver "
                        "cuantos formatos distintos hay de verdad en el archivo."),
                unsafe_allow_html=True)
    st.dataframe(insp["formatos"], use_container_width=True, hide_index=True)
