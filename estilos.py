"""
Estilos de la app.

Se separa del app.py para que el CSS no se mezcle con la lógica de pantalla.

ADVERTENCIA: parte de este CSS apunta a clases internas de Streamlit
(data-testid). Streamlit puede cambiarlas entre versiones. Si algún dia la
app se ve rara despues de una actualizacion, el sospechoso es este archivo:
borrarlo no rompe nada funcional, solo el aspecto.

Paleta
------
Carmin   #C80651   color corporativo, se usa con avaricia: solo para lo que
                   el programa esta dispuesto a firmar
Tinta    #14131A   texto y encabezados
Hueso    #FAF8F6   fondo, papel calido
Piedra   #6B6875   texto secundario
Humo     #E4DFDB   bordes y divisiones
Ambar    #B8801F   banda intermedia (revisar candidatos)

La escala de bandas es una escalera de confianza, no tres categorias sueltas:
carmin (firma) -> ambar (duda) -> piedra (nada). El color codifica cuanta
autoridad tiene el programa sobre esa fila.
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --carmin: #C80651;
    --carmin-suave: #FBEAF0;
    --tinta: #14131A;
    --hueso: #FAF8F6;
    --piedra: #6B6875;
    --humo: #E4DFDB;
    --ambar: #B8801F;
    --ambar-suave: #FBF3E4;
}

/* ---------- Tipografia ---------- */

html, body, [class*="css"], .stMarkdown, .stButton, label {
    font-family: 'Jost', -apple-system, 'Segoe UI', sans-serif;
}

h1, h2, h3 {
    font-family: 'Jost', sans-serif !important;
    letter-spacing: -0.02em;
    color: var(--tinta);
}

h1 {
    font-weight: 600 !important;
    font-size: 2.1rem !important;
    line-height: 1.1;
}

h2 {
    font-weight: 500 !important;
    font-size: 1.15rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--piedra) !important;
    border-bottom: 1px solid var(--humo);
    padding-bottom: 0.4rem;
    margin-top: 2.4rem !important;
}

/* Los textos del FBL3N son cadenas de digitos que hay que comparar
   caracter por caracter. Monoespaciada no es adorno: es lo que permite
   ver que 00033 no es 00038. */
[data-testid="stDataFrame"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.82rem;
}

/* ---------- Encabezado ---------- */

.def cabecera():
    svg = " ".join(MARCA_SVG.split())
    return (
        '<div class="cabecera">'
        '<div class="lockup">'
        f'{svg}'
        '<div class="lockup-texto">'
        '<div class="equipo">Payments <span>LAC</span></div>'
        '<div class="herramienta">Asistente para BOAS</div>'
        '</div></div>'
        '<div class="bajada">'
        'Compara los textos del FBL3N contra las plantillas del glosario de cada '
        'pais. <strong>El programa solo recomienda:</strong> la actualizacion del '
        'documento historico sigue siendo manual.'
        '</div></div>'
    )

.cabecera .lockup {
    display: flex;
    align-items: center;
    gap: 0.85rem;
}

.cabecera .lockup svg {
    flex-shrink: 0;
}

.cabecera .equipo {
    font-size: 0.68rem;
    font-weight: 500;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--piedra);
    line-height: 1;
    margin-bottom: 0.3rem;
}

.cabecera .equipo span {
    color: var(--carmin);
}

.cabecera .herramienta {
    font-family: 'Jost', sans-serif;
    font-size: 1.85rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--tinta);
    line-height: 1;
}

.cabecera h1 {
    margin: 0 !important;
    padding: 0 !important;
}

.cabecera .bajada {
    color: var(--piedra);
    font-size: 0.92rem;
    margin-top: 0.35rem;
    max-width: 62ch;
    line-height: 1.5;
}

.cabecera .bajada strong {
    color: var(--tinta);
    font-weight: 500;
}

/* ---------- Escalera de confianza ---------- */

.escalera {
    display: flex;
    width: 100%;
    height: 40px;
    border-radius: 3px;
    overflow: hidden;
    margin: 0.2rem 0 0.5rem 0;
    border: 1px solid var(--humo);
}

.escalera .tramo {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.78rem;
    font-weight: 500;
    color: #fff;
    min-width: 0;
    overflow: hidden;
    white-space: nowrap;
    transition: flex-grow 0.4s ease;
}

.tramo.directa  { background: var(--carmin); }
.tramo.revisar  { background: var(--ambar); }
.tramo.manual   { background: var(--piedra); }

.leyenda {
    display: flex;
    gap: 1.6rem;
    flex-wrap: wrap;
    margin-bottom: 1.6rem;
}

.leyenda .item {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    font-size: 0.82rem;
    color: var(--piedra);
}

.leyenda .punto {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
    transform: translateY(-1px);
}

.leyenda .cifra {
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
    color: var(--tinta);
}

/* ---------- Fichas de dato ---------- */

.fichas {
    display: flex;
    gap: 0;
    border: 1px solid var(--humo);
    border-radius: 3px;
    background: #fff;
    overflow: hidden;
    margin-bottom: 0.6rem;
}

.ficha {
    flex: 1;
    padding: 0.85rem 1.1rem;
    border-right: 1px solid var(--humo);
}

.ficha:last-child { border-right: none; }

.ficha .rotulo {
    font-size: 0.66rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--piedra);
    margin-bottom: 0.3rem;
}

.ficha .valor {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.45rem;
    font-weight: 500;
    color: var(--tinta);
    line-height: 1;
}

.ficha .valor.tachado {
    color: var(--piedra);
    text-decoration: line-through;
    text-decoration-thickness: 1px;
}

/* ---------- Avisos ---------- */

.nota {
    border-left: 2px solid var(--humo);
    padding: 0.15rem 0 0.15rem 0.9rem;
    color: var(--piedra);
    font-size: 0.84rem;
    line-height: 1.5;
    margin: 0.5rem 0 1.2rem 0;
}

.nota.alerta {
    border-left-color: var(--ambar);
    background: var(--ambar-suave);
    padding: 0.7rem 0.9rem;
    border-radius: 0 3px 3px 0;
}

/* ---------- Controles ---------- */

.stButton > button, .stDownloadButton > button {
    font-family: 'Jost', sans-serif;
    font-weight: 500;
    letter-spacing: 0.03em;
    border-radius: 3px;
    border: 1px solid var(--carmin);
    transition: all 0.15s ease;
}

.stDownloadButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 3px 10px rgba(200, 6, 81, 0.18);
}

[data-testid="stSidebar"] {
    background: #fff;
    border-right: 1px solid var(--humo);
}

[data-testid="stFileUploader"] section {
    border: 1px dashed var(--humo);
    border-radius: 3px;
    background: var(--hueso);
}

.stTabs [data-baseweb="tab-list"] {
    gap: 1.8rem;
    border-bottom: 1px solid var(--humo);
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Jost', sans-serif;
    font-size: 0.88rem;
    letter-spacing: 0.03em;
    padding: 0.4rem 0;
}

/* Respeta a quien pidio menos movimiento */
@media (prefers-reduced-motion: reduce) {
    *, .escalera .tramo, .stDownloadButton > button {
        transition: none !important;
        animation: none !important;
    }
}
</style>
"""


COLORES_BANDA = {
    "recomendacion directa": ("directa", "#C80651"),
    "revisar candidatos": ("revisar", "#B8801F"),
    "revision manual": ("manual", "#6B6875"),
}

ORDEN_ESCALERA = ["recomendacion directa", "revisar candidatos", "revision manual"]


# Marca del equipo. No es el logotipo corporativo de Diageo: identifica al
# equipo que mantiene la herramienta.
#
# Las tres barras son la escalera de confianza en miniatura — carmin, ambar,
# piedra — en el mismo orden y con los mismos colores que la barra grande de
# la pantalla. La marca dice lo que hace el programa: repartir filas en tres
# grados de certeza.
MARCA_SVG = """
<svg width="30" height="30" viewBox="0 0 30 30" fill="none"
     xmlns="http://www.w3.org/2000/svg" role="img"
     aria-label="Payments LAC">
  <rect x="2"  y="5"  width="26" height="5" rx="1" fill="#C80651"/>
  <rect x="2"  y="12.5" width="17" height="5" rx="1" fill="#B8801F"/>
  <rect x="2"  y="20" width="9"  height="5" rx="1" fill="#6B6875"/>
</svg>
"""


def cabecera():
    return f"""
<div class="cabecera">
  <div class="lockup">
    {MARCA_SVG}
    <div class="lockup-texto">
      <div class="equipo">Payments <span>LAC</span></div>
      <div class="herramienta">Asistente para BOAS</div>
    </div>
  </div>
  <div class="bajada">
    Compara los textos del FBL3N contra las plantillas del glosario de cada pais.
    <strong>El programa solo recomienda:</strong> la actualizacion del documento
    historico sigue siendo manual.
  </div>
</div>
"""


def escalera(conteos, total):
    """Barra apilada: que porcion de las filas esta dispuesto a firmar el programa.

    Es la primera cosa que se ve porque es la unica pregunta que importa antes
    de mirar ninguna fila.
    """
    if not total:
        return ""

    tramos, leyenda = [], []
    for banda in ORDEN_ESCALERA:
        n = conteos.get(banda, 0)
        if not n:
            continue
        clase, color = COLORES_BANDA[banda]
        pct = 100 * n / total
        etiqueta = f"{pct:.0f}%" if pct >= 7 else ""
        tramos.append(
            f'<div class="tramo {clase}" style="flex-grow:{n}" '
            f'title="{banda}: {n} filas">{etiqueta}</div>'
        )
        leyenda.append(
            f'<div class="item"><span class="punto" style="background:{color}"></span>'
            f'{banda} <span class="cifra">{n:,}</span> filas &middot; '
            f'<span class="cifra">{pct:.1f}%</span></div>'
        )

    return (f'<div class="escalera">{"".join(tramos)}</div>'
            f'<div class="leyenda">{"".join(leyenda)}</div>')


def fichas(items):
    """items: lista de (rotulo, valor, tachado)."""
    celdas = []
    for rotulo, valor, tachado in items:
        clase = "valor tachado" if tachado else "valor"
        celdas.append(f'<div class="ficha"><div class="rotulo">{rotulo}</div>'
                      f'<div class="{clase}">{valor}</div></div>')
    return f'<div class="fichas">{"".join(celdas)}</div>'


def nota(texto, alerta=False):
    clase = "nota alerta" if alerta else "nota"
    return f'<div class="{clase}">{texto}</div>'
