"""
Motor de clasificacion BOAS.

Este modulo no sabe nada de Streamlit ni de Colab: solo recibe DataFrames y
devuelve DataFrames. Toda la interfaz vive en app.py.

Dos capas conviven:
  - ANCLAS: se verifican sobre el TEXTO CRUDO. Unica capa capaz de distinguir
    dos categorias que solo difieren en unos digitos internos.
  - SIMILITUD: se calcula sobre el TEXTO NORMALIZADO. Como la normalizacion
    borra los bloques de digitos, es ciega al digito discriminador y por eso
    nunca puede llegar a recomendacion directa (techo de 84 puntos).
"""

import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

import pandas as pd

# --------------------------------------------------------------------------
# Parametros del motor
# --------------------------------------------------------------------------

MAPA_PAIS = {
    "7100": "BRASIL",          "7250": "PANAMA",
    "7260": "COSTA RICA",      "7271": "REP. DOMINICANA",
    "7351": "VENEZUELA",       "7600": "PARAGUAY",
    "7510": "MEXICO",          "7511": "MEXICO",
    "7512": "MEXICO",          "7513": "MEXICO",
    "7530": "MEXICO",          "7650": "COLOMBIA",
    "7660": "CHILE",           "7670": "PERU",
    "7700": "URUGUAY",
}

MIN_ANCLA_CHARS = 6     # minimo de caracteres literales para aceptar una plantilla
PISO_ANCLA = 90         # puntaje minimo cuando una plantilla ancla
TECHO_SIMILITUD = 84    # sin anclas nunca se cruza el umbral de 85
UMBRAL_DIRECTA = 85
UMBRAL_CANDIDATOS = 60
PROP_GENERICA = 0.6     # plantilla que toca mas de este % de textos es sospechosa

COLS_SALIDA = ["pais", "Document Number", "Text", "banda", "puntaje",
               "CONCEPT", "ACTION"]

ANCHOS = {"pais": 16, "Document Number": 16, "Text": 55,
          "banda": 22, "puntaje": 9, "CONCEPT": 26, "ACTION": 40}

ORDEN_BANDA = {"recomendacion directa": 0, "revisar candidatos": 1,
               "revision manual": 2}

COMODINES = re.compile(r"\*+|\(\s*NUMERO[^)]*\)|\?+")


# --------------------------------------------------------------------------
# Normalizacion de texto
# --------------------------------------------------------------------------

def limpiar(s):
    """Neutraliza espacios duros que viajan al copiar desde SAP."""
    s = str(s).replace("\xa0", " ").replace("\u2007", " ").replace("\u202f", " ")
    return re.sub(r"\s+", " ", s).strip()


def norm_nombre(s):
    """Normaliza nombres de hoja/pais: sin tildes, sin puntos, sin espacios."""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Z]", "", s)


def limpiar_codigo(v):
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def normalizar(t):
    """Solo para el puntaje de similitud. NUNCA para agrupar ni para anclas."""
    s = limpiar(t).upper()
    s = re.sub(r"\d{6,}", "#", s)   # bloques largos -> un comodin
    s = re.sub(r"\d{2,5}", "@", s)  # bloques cortos -> otro comodin
    return s


def firma(t):
    """Firma estructural: corridas de digitos -> D, de letras -> A."""
    return re.sub(r"\d+", "D", re.sub(r"[A-Za-z]+", "A", t))


# --------------------------------------------------------------------------
# Compilador de anclas
# --------------------------------------------------------------------------

def compilar(plantilla, modo="prefijo"):
    """Convierte una plantilla del glosario en un patron sobre texto crudo.

    Parte por los comodines (*, (NUMERO), ? son equivalentes), escapa cada
    segmento literal y los une con un comodin no-codicioso. La CANTIDAD de
    asteriscos no importa.
    """
    p = limpiar(plantilla)
    trozos = COMODINES.split(p)
    piezas, anclas = [], []
    for i, t in enumerate(trozos):
        if t:
            piezas.append(re.escape(t))
            anclas.append(t)
        if i < len(trozos) - 1:
            piezas.append(".*?")
    cuerpo = "".join(piezas)
    patron = {"estricto": f"^{cuerpo}$",
              "prefijo": f"^{cuerpo}",
              "libre": cuerpo}[modo]
    return {
        "regex": re.compile(patron, re.IGNORECASE),
        "n_chars": sum(len(a) for a in anclas),
        "n_digitos": sum(len(re.findall(r"\d", a)) for a in anclas),
    }


def preparar_glosario(df):
    """Compila las plantillas de una hoja una sola vez.

    Devuelve (activas, descartadas). Se descartan las que no alcanzan el
    minimo de caracteres ancla, para que plantillas casi vacias no hagan
    match con todo.
    """
    items, descartadas = [], []
    for _, r in df.iterrows():
        pl = r.get("BOA Concept")
        if pd.isna(pl) or not limpiar(pl):
            continue
        c = compilar(pl, "prefijo")
        reg = {"plantilla": limpiar(pl), "concept": r.get("CONCEPT"),
               "action": r.get("ACTION"), **c}
        if c["n_chars"] < MIN_ANCLA_CHARS:
            descartadas.append(reg)
        else:
            items.append(reg)
    return items, descartadas


# --------------------------------------------------------------------------
# Puntaje de similitud
# --------------------------------------------------------------------------

def jaccard(a, b):
    ta = set(re.findall(r"[A-Z@#]+", a))
    tb = set(re.findall(r"[A-Z@#]+", b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def puntaje_similitud(texto, plantilla):
    a, b = normalizar(texto), normalizar(plantilla)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        cobertura = min(len(a), len(b)) / max(len(a), len(b))
        return 60 + 40 * cobertura        # regla de contencion
    sec = SequenceMatcher(None, a, b).ratio()
    return 100 * (0.6 * sec + 0.4 * jaccard(a, b))


# --------------------------------------------------------------------------
# Motor de decision
# --------------------------------------------------------------------------

def clasificar(texto, items):
    """Anclas mandan sobre similitud.

    Si al menos una plantilla ancla, solo compiten las que anclaron y gana la
    mas especifica. Si ninguna ancla, la similitud decide pero con techo: nunca
    llega a recomendacion directa.
    """
    t = limpiar(texto)
    anclan = [g for g in items if g["regex"].search(t)]
    empate = False

    if anclan:
        anclan.sort(key=lambda g: (-g["n_chars"], -g["n_digitos"]))
        if len(anclan) > 1:
            empate = (anclan[0]["n_chars"] == anclan[1]["n_chars"]
                      and anclan[0]["concept"] != anclan[1]["concept"])
        mejor = anclan[0]
        pt = max(PISO_ANCLA, puntaje_similitud(t, mejor["plantilla"]))
        via = "ancla"
    elif items:
        pt, mejor = -1.0, None
        for g in items:
            p = min(TECHO_SIMILITUD, puntaje_similitud(t, g["plantilla"]))
            if p > pt:
                pt, mejor = p, g
        via = "similitud"
    else:
        return {"banda": "revision manual", "puntaje": 0,
                "concept": None, "action": None, "via": "sin glosario"}

    if empate:
        banda = "revisar candidatos"        # ambiguedad real: no recomendar
    elif pt >= UMBRAL_DIRECTA:
        banda = "recomendacion directa"
    elif pt >= UMBRAL_CANDIDATOS:
        banda = "revisar candidatos"
    else:
        banda = "revision manual"

    directa = (banda == "recomendacion directa")
    return {
        "banda": banda,
        "puntaje": round(pt, 1),
        "concept": mejor["concept"] if banda != "revision manual" else None,
        "action": mejor["action"] if directa else None,
        "via": via,
    }


# --------------------------------------------------------------------------
# Carga y depuracion
# --------------------------------------------------------------------------

def cargar_fbl3n(archivo):
    """Lee el FBL3N. Todo como texto: si pandas lo lee como numero, se pierden
    los ceros a la izquierda, que son anclas.
    """
    df = pd.read_excel(archivo, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    faltan = [c for c in ["Company Code", "Text"] if c not in df.columns]
    if faltan:
        raise ValueError(f"Al FBL3N le faltan columnas obligatorias: {faltan}. "
                         f"Columnas encontradas: {list(df.columns)}")
    if "Document Number" not in df.columns:
        df["Document Number"] = ""
    return df


def depurar(df):
    """Mapea pais y ELIMINA las filas con texto en blanco.

    Devuelve (df_depurado, info). Las filas eliminadas no vuelven a aparecer
    en ninguna etapa posterior.
    """
    d = df.copy()
    d["_codigo"] = d["Company Code"].map(limpiar_codigo)
    d["pais"] = d["_codigo"].map(MAPA_PAIS)
    d["_texto_crudo"] = d["Text"].fillna("").astype(str).map(limpiar)

    n_original = len(d)
    n_vacias = int((d["_texto_crudo"] == "").sum())
    d = d[d["_texto_crudo"] != ""].copy()

    sin_mapeo = sorted(d.loc[d["pais"].isna(), "_codigo"].unique().tolist())
    d["pais"] = d["pais"].fillna("SIN MAPEO")

    info = {
        "n_original": n_original,
        "n_vacias": n_vacias,
        "n_proceso": len(d),
        "sin_mapeo": sin_mapeo,
        "n_sin_mapeo": int((d["pais"] == "SIN MAPEO").sum()),
        "textos_unicos": int(d["_texto_crudo"].nunique()),
    }
    return d, info


def cargar_glosario(archivo):
    """Devuelve {nombre_normalizado: (nombre_hoja, DataFrame)}."""
    libro = pd.ExcelFile(archivo)
    glosarios = {}
    for hoja in libro.sheet_names:
        df = libro.parse(hoja, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        glosarios[norm_nombre(hoja)] = (hoja, df)
    return glosarios


def hoja_valida(glosarios, pais):
    """True si existe hoja para el pais y tiene la columna de plantillas."""
    k = norm_nombre(pais)
    return k in glosarios and "BOA Concept" in glosarios[k][1].columns


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

def procesar(df, glosarios):
    """Enruta cada fila al glosario de SU pais y clasifica.

    El cache esta indexado por TEXTO CRUDO: dos textos que normalizan igual
    pero difieren en el crudo son entradas distintas y pueden recibir
    clasificaciones distintas. Esa es la correccion estructural de la falla
    de la version anterior.
    """
    resultados, detalle = [], []

    for pais in sorted(df["pais"].unique()):
        sub = df[df["pais"] == pais]
        k = norm_nombre(pais)

        if not hoja_valida(glosarios, pais):
            for _, r in sub.iterrows():
                resultados.append({**r.to_dict(), "banda": "revision manual",
                                   "puntaje": 0, "concept": None,
                                   "action": None, "via": "sin glosario"})
            detalle.append({"pais": pais, "hoja": None, "plantillas": 0,
                            "descartadas": 0, "filas": len(sub),
                            "textos_unicos": int(sub["_texto_crudo"].nunique())})
            continue

        items, desc = preparar_glosario(glosarios[k][1])
        cache = {}
        for _, r in sub.iterrows():
            t = r["_texto_crudo"]
            if t not in cache:              # cache por TEXTO CRUDO
                cache[t] = clasificar(t, items)
            resultados.append({**r.to_dict(), **cache[t]})

        detalle.append({"pais": pais, "hoja": glosarios[k][0],
                        "plantillas": len(items), "descartadas": len(desc),
                        "filas": len(sub), "textos_unicos": len(cache)})

    return pd.DataFrame(resultados), pd.DataFrame(detalle)


def metricas(res):
    """Conteo y porcentaje de filas por banda, por pais."""
    filas = []
    for pais, g in res.groupby("pais"):
        for banda, n in g["banda"].value_counts().items():
            filas.append({"pais": pais, "banda": banda, "filas": int(n),
                          "porcentaje": round(100 * n / len(g), 1)})
        filas.append({"pais": pais, "banda": "-- via ancla",
                      "filas": int((g["via"] == "ancla").sum()),
                      "porcentaje": round(100 * (g["via"] == "ancla").sum() / len(g), 1)})
    return pd.DataFrame(filas)


def tabla_final(res):
    """Ordena por pais y banda (recomendacion directa primero)."""
    f = res.rename(columns={"concept": "CONCEPT", "action": "ACTION"}).copy()
    f["_ord"] = f["banda"].map(ORDEN_BANDA)
    f = f.sort_values(["pais", "_ord", "puntaje"], ascending=[True, True, False])
    for c in COLS_SALIDA:
        if c not in f.columns:
            f[c] = ""
    return f[COLS_SALIDA]


def exportar_excel(final, buffer):
    """Escribe el Excel con anchos ajustados, paneles congelados y autofiltro."""
    with pd.ExcelWriter(buffer, engine="openpyxl") as w:
        final.to_excel(w, index=False, sheet_name="RECOMENDACIONES")
        ws = w.sheets["RECOMENDACIONES"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for i, c in enumerate(final.columns, start=1):
            letra = ws.cell(row=1, column=i).column_letter
            ws.column_dimensions[letra].width = ANCHOS.get(c, 18)
    return buffer


# --------------------------------------------------------------------------
# Auditoria de glosario
# --------------------------------------------------------------------------

def auditar(items, textos_unicos, conteos):
    """Control de calidad del glosario de un pais.

    OJO: que una plantilla no matchee NO significa que este mal escrita.
    Puede ser que esa categoria simplemente no aparecio en este archivo.
    Verificar en los datos antes de corregir.
    """
    N = len(textos_unicos)
    TOT = sum(conteos)

    cobertura, sin_match, genericas = {}, [], []
    for idx_g, g in enumerate(items):
        idx = [i for i, t in enumerate(textos_unicos) if g["regex"].search(t)]
        cobertura[idx_g] = set(idx)
        if not idx:
            sin_match.append({"CONCEPT": g["concept"], "plantilla": g["plantilla"]})
        elif len(idx) > PROP_GENERICA * N:
            genericas.append({"CONCEPT": g["concept"], "plantilla": g["plantilla"],
                              "textos": len(idx),
                              "filas": sum(conteos[i] for i in idx)})

    conflictos = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if a["concept"] == b["concept"]:
                continue
            inter = cobertura[i] & cobertura[j]
            if inter and a["n_chars"] == b["n_chars"]:
                conflictos.append({"CONCEPT A": a["concept"], "CONCEPT B": b["concept"],
                                   "textos en conflicto": len(inter)})

    cub = set().union(*cobertura.values()) if cobertura else set()
    sin = [i for i in range(N) if i not in cub]
    filas_sin = sum(conteos[i] for i in sin)
    descubiertos = sorted(({"filas": conteos[i], "Text": textos_unicos[i]} for i in sin),
                          key=lambda x: -x["filas"])

    return {
        "n_plantillas": len(items),
        "n_textos": N,
        "n_filas": TOT,
        "cobertura_filas": TOT - filas_sin,
        "cobertura_pct": round(100 * (TOT - filas_sin) / TOT, 1) if TOT else 0.0,
        "sin_match": pd.DataFrame(sin_match),
        "genericas": pd.DataFrame(genericas),
        "conflictos": pd.DataFrame(conflictos),
        "descubiertos": pd.DataFrame(descubiertos),
    }


def auditar_pais(df, glosarios, pais):
    """Prepara los insumos y corre la auditoria para un pais."""
    if not hoja_valida(glosarios, pais):
        return None
    items, _ = preparar_glosario(glosarios[norm_nombre(pais)][1])
    vc = df[df["pais"] == pais]["_texto_crudo"].value_counts()
    if vc.empty:
        return None
    return auditar(items, list(vc.index), [int(v) for v in vc.values])


def inspeccionar(df, pais=None):
    """Diagnostico de los textos crudos: top repetidos y formatos estructurales."""
    sub = df if pais is None else df[df["pais"] == pais]
    vc = sub["_texto_crudo"].value_counts()
    formatos = Counter(firma(t) for t in vc.index).most_common(15)
    return {
        "top": pd.DataFrame({"filas": vc.values[:15], "Text": vc.index[:15]}),
        "formatos": pd.DataFrame(formatos, columns=["firma", "textos unicos"]),
        "n_textos": len(vc),
        "n_filas": int(vc.sum()),
    }
