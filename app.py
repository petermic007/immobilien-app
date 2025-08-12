import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from numpy_financial import irr

# ---------------------------------------------------------
# Basis-Setup (mobilfreundlich)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Immobilien-Kaufentscheidung",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.caption("📌 Version: V1.1")
st.title("🏠 Immobilien-Kaufentscheidung: Eigenkapital-Rendite & IRR")

# ---------------------------------------------------------
# Eingaben (kompakter – Basics oben, Details im Expander)
# ---------------------------------------------------------
verfuegbares_gesamt_ek = st.slider("Verfügbares Anfangs-Eigenkapital (€)", 120000, 1000000, 500000, step=10000)

col1, col2 = st.columns(2)
with col1:
    kaufpreis = st.number_input("Kaufpreis der Immobilie (€)", value=650000, step=10000, format="%d")
    ek_quote = st.number_input("Eigenkapitalquote (%)", value=20.0, step=1.0) / 100
    laufzeit_jahre = st.number_input("Laufzeit des Kredits (Jahre)", value=10, step=1, format="%d")
with col2:
    zins_p_a = st.slider("Zinssatz p.a. (%)", 1.0, 6.0, 3.45, 0.05) / 100
    tilgung_p_a = st.slider("Anfangstilgung p.a. (%)", 1.0, 5.0, 1.5, 0.1) / 100
    miete_monatlich = st.number_input("Kaltmiete pro Monat (€)", value=round(650000 * 0.035 / 12), step=50, format="%d")

with st.expander("Erweiterte Annahmen"):
    wertsteigerung_p_a = st.slider("Wertsteigerung Immobilie p.a. (%)", 0.0, 5.0, 2.5, 0.1) / 100
    mietsteigerung_p_a = st.slider("Kaltmieten-Steigerung p.a. (%)", 0.0, 6.0, 3.0, 0.1) / 100
    laufende_kosten_p_a = st.number_input("Laufende Kosten p.a. (% vom Immobilienwert)", value=0.5, step=0.1) / 100
    aktien_rendite_p_a = st.number_input("Rendite p.a. Aktienmarkt (%)", value=7.5, step=0.1) / 100

# Reset-Button (praktisch auf dem Handy)
if st.button("🔄 Zurücksetzen"):
    st.experimental_rerun()

# ---------------------------------------------------------
# Caching der Berechnung (für flüssige UX)
# ---------------------------------------------------------
@st.cache_data
def sim(
    verfuegbares_gesamt_ek: int,
    kaufpreis: int,
    ek_quote: float,
    zins_p_a: float,
    tilgung_p_a: float,
    wertsteigerung_p_a: float,
    mietsteigerung_p_a: float,
    laufzeit_jahre: int,
    laufende_kosten_p_a: float,
    miete_monatlich: int,
    aktien_rendite_p_a: float
):
    # Transaktionskosten
    makler = 0.0357
    notar = 0.015
    steuer = 0.05
    grundbuch = 0.005
    transaktionskosten_quote = makler + notar + steuer + grundbuch

    # Finanzierungsparameter
    monate = laufzeit_jahre * 12
    zins_p_m = zins_p_a / 12
    tilgung_p_m = tilgung_p_a / 12
    annuitaet_p_m = (zins_p_a + tilgung_p_a) * (1 - ek_quote) * kaufpreis / 12

    kreditbetrag = (1 - ek_quote) * kaufpreis
    ek_ohne_transaktionskosten = ek_quote * kaufpreis
    transaktionskosten = kaufpreis * transaktionskosten_quote
    ek_mit_transaktionskosten = ek_ohne_transaktionskosten + transaktionskosten
    verbleibendes_ek_kauf = max(0, verfuegbares_gesamt_ek - ek_mit_transaktionskosten)

    # Listen
    zins_list, tilgung_list, restschuld_list = [], [], []
    wert_list, kosten_list, miete_list, cashflow_list = [], [], [], []
    ek_kauf_verlauf, vermoegen_miete_verlauf, sparraten = [], [], []

    restschuld = kreditbetrag
    immowert = kaufpreis
    kumulierte_kosten = transaktionskosten
    kapital_sparplan = 0
    kumulative_negative_differenzen = 0
    negativer_sparmonat = None

    for monat in range(1, monate + 1):
        zins = restschuld * zins_p_m
        tilgung = annuitaet_p_m - zins
        restschuld = max(0, restschuld - tilgung)
        immowert *= (1 + wertsteigerung_p_a / 12)
        kosten = immowert * laufende_kosten_p_a / 12
        kumulierte_kosten += kosten + zins
        aktuelle_miete = miete_monatlich * ((1 + mietsteigerung_p_a / 12) ** monat)

        cf = -kosten + (aktuelle_miete - zins)
        if monat == 1:
            cf -= ek_mit_transaktionskosten
        cashflow_list.append(cf)

        zins_list.append(zins)
        tilgung_list.append(tilgung)
        restschuld_list.append(restschuld)
        wert_list.append(immowert)
        miete_list.append(aktuelle_miete)

        # Sparrate & Vermögensaufbau Miete
        diff = annuitaet_p_m - aktuelle_miete
        sparraten.append(diff)
        if diff >= 0:
            kapital_sparplan = (kapital_sparplan + diff) * (1 + aktien_rendite_p_a / 12)
        else:
            kumulative_negative_differenzen += abs(diff)
            if negativer_sparmonat is None:
                negativer_sparmonat = monat

        # Szenario Miete
        vermoegen_miete = verfuegbares_gesamt_ek * ((1 + aktien_rendite_p_a / 12) ** monat) + kapital_sparplan
        vermoegen_miete_verlauf.append(vermoegen_miete)

        # Szenario Kauf
        ek_kauf = immowert - restschuld
        ek_kauf += verbleibendes_ek_kauf * ((1 + aktien_rendite_p_a / 12) ** monat)
        ek_kauf_verlauf.append(ek_kauf)

    # Endwerte Kauf
    wert_am_ende = wert_list[-1]
    restschuld_am_ende = restschuld_list[-1]
    ek_in_immobilie = wert_am_ende - restschuld_am_ende
    rendite_pa_mit_transaktionskosten = (ek_kauf_verlauf[-1] / ek_mit_transaktionskosten) ** (1 / laufzeit_jahre) - 1
    cashflow_list[-1] += ek_in_immobilie
    irr_ohne_transaktionskosten = irr(cashflow_list)

    # Vergleich Miete
    miete_am_ende = miete_list[-1]
    sparrate_anfang = annuitaet_p_m - miete_list[0]
    sparrate_ende = annuitaet_p_m - miete_list[-1]
    endwert_miete_gesamt = vermoegen_miete_verlauf[-1] - kumulative_negative_differenzen
    diff_abs = ek_kauf_verlauf[-1] - endwert_miete_gesamt
    rel_diff = diff_abs / endwert_miete_gesamt if endwert_miete_gesamt != 0 else 0

    return {
        "monate": monate,
        "annuitaet_p_m": annuitaet_p_m,
        "kreditbetrag": kreditbetrag,
        "ek_mit_transaktionskosten": ek_mit_transaktionskosten,
        "verbleibendes_ek_kauf": verbleibendes_ek_kauf,
        "zins_list": zins_list,
        "tilgung_list": tilgung_list,
        "restschuld_list": restschuld_list,
        "wert_list": wert_list,
        "miete_list": miete_list,
        "cashflow_list": cashflow_list,
        "ek_kauf_verlauf": ek_kauf_verlauf,
        "vermoegen_miete_verlauf": vermoegen_miete_verlauf,
        "sparraten": sparraten,
        "negativer_sparmonat": negativer_sparmonat,
        "kumulative_negative_differenzen": kumulative_negative_differenzen,
        "wert_am_ende": wert_am_ende,
        "restschuld_am_ende": restschuld_am_ende,
        "ek_in_immobilie": ek_in_immobilie,
        "rendite_pa_mit_transaktionskosten": rendite_pa_mit_transaktionskosten,
        "irr_ohne_transaktionskosten": irr_ohne_transaktionskosten,
        "miete_am_ende": miete_am_ende,
        "sparrate_anfang": sparrate_anfang,
        "sparrate_ende": sparrate_ende,
        "endwert_miete_gesamt": endwert_miete_gesamt,
        "diff_abs": diff_abs,
        "rel_diff": rel_diff
    }

# Lauf der Simulation
res = sim(
    verfuegbares_gesamt_ek,
    kaufpreis,
    ek_quote,
    zins_p_a,
    tilgung_p_a,
    wertsteigerung_p_a,
    mietsteigerung_p_a,
    laufzeit_jahre,
    laufende_kosten_p_a,
    miete_monatlich,
    aktien_rendite_p_a
)

# ---------------------------------------------------------
# Ausgabe in Tabs
# ---------------------------------------------------------
tab_kauf, tab_miete, tab_vergleich, tab_charts = st.tabs(["🏡 Kauf", "📦 Miete", "🤝 Vergleich", "📈 Charts"])

with tab_kauf:
    st.subheader("Vermögensaufbau Szenario Kauf")
    st.write(f"**Gesamt verfügbares Anfangs-Eigenkapital:** € {verfuegbares_gesamt_ek:,.2f}")
    st.write(f"**Eingesetztes Eigenkapital (Kauf):** € {res['ek_mit_transaktionskosten']:,.2f}")
    st.write(f"**Verbleibendes Eigenkapital im Aktienmarkt:** € {res['verbleibendes_ek_kauf']:,.2f}")
    st.write(f"**Annuität pro Monat:** € {res['annuitaet_p_m']:,.2f}")
    st.write(f"**Zinszahlung im 1. Monat:** € {res['zins_list'][0]:,.2f}")
    st.write(f"**Zinszahlung im letzten Monat:** € {res['zins_list'][-1]:,.2f}")
    st.write(f"**Tilgung im 1. Monat:** € {res['tilgung_list'][0]:,.2f}")
    st.write(f"**Tilgung im letzten Monat:** € {res['tilgung_list'][-1]:,.2f}")
    st.write(f"**Kredithöhe zu Beginn:** € {res['kreditbetrag']:,.2f}")
    st.write(f"**Wert der Immobilie am Laufzeitende:** € {res['wert_am_ende']:,.2f}")
    st.write(f"**Restschuld nach {laufzeit_jahre} Jahren:** € {res['restschuld_am_ende']:,.2f}")
    st.write(f"**Vermögen (EK in Immobilie + restliches EK):** € {res['ek_kauf_verlauf'][-1]:,.2f}")
    st.write(f"**Vereinfachte EK-Rendite p.a.:** {res['rendite_pa_mit_transaktionskosten'] * 100:.2f} %")
    st.write(f"**Interne Eigenkapitalrendite (IRR):** {res['irr_ohne_transaktionskosten'] * 100:.2f} %")

with tab_miete:
    st.subheader("Vermögensaufbau Szenario Miete")
    st.write(f"**Kaltmiete (Start):** € {res['miete_list'][0]:,.2f}")
    st.write(f"**Kaltmiete am Ende:** € {res['miete_am_ende']:,.2f}")
    st.write(f"**Sparrate (Start):** € {res['sparrate_anfang']:,.2f}")
    st.write(f"**Sparrate (Ende):** € {res['sparrate_ende']:,.2f}")
    if res["negativer_sparmonat"]:
        jahre = res["negativer_sparmonat"] // 12
        monate_rest = res["negativer_sparmonat"] % 12
        st.write(f"⚠️ Sparrate wird negativ ab: Jahr {jahre}, Monat {monate_rest}")
    st.write(f"**Unverzinste Zusatzkosten (Miete > Annuität):** € {res['kumulative_negative_differenzen']:,.2f}")
    st.write(f"**Vermögen nach Anlage (inkl. Sparplan):** € {res['endwert_miete_gesamt']:,.2f}")
    st.write(f"**Anfangskapital (voll investiert):** € {verfuegbares_gesamt_ek:,.2f}")

with tab_vergleich:
    st.subheader("Kaufen vs. Mieten")
    st.write(f"**Vermögen Kauf:** € {res['ek_kauf_verlauf'][-1]:,.2f}")
    st.write(f"**Vermögen Miete + Anlage:** € {res['endwert_miete_gesamt']:,.2f}")
    st.write(f"**Differenz:** € {res['diff_abs']:,.2f} ({res['rel_diff'] * 100:.2f} %)")

with tab_charts:
    st.subheader("Vermögensentwicklung über Zeit")
    fig1, ax1 = plt.subplots()
    ax1.plot(range(1, res["monate"] + 1), res["ek_kauf_verlauf"], label="Kaufen: Vermögen")
    ax1.plot(range(1, res["monate"] + 1), res["vermoegen_miete_verlauf"], label="Mieten: Vermögen")
    ax1.set_xlabel("Monat")
    ax1.set_ylabel("Vermögen (€)")
    ax1.set_title("Vermögensentwicklung über Zeit")
    ax1.legend()
    st.pyplot(fig1)

    st.subheader("Sparrate vs. Miete vs. Annuität")
    fig2, ax2 = plt.subplots()
    ax2.plot(range(1, res["monate"] + 1), res["sparraten"], label="Sparrate")
    ax2.plot(range(1, res["monate"] + 1), [res["annuitaet_p_m"]] * res["monate"], label="Annuität")
    ax2.plot(range(1, res["monate"] + 1), res["miete_list"], label="Kaltmiete")
    ax2.set_xlabel("Monat")
    ax2.set_ylabel("Beträge (€)")
    ax2.set_title("Sparrate vs. Miete vs. Annuität")
    ax2.legend()
    st.pyplot(fig2)
