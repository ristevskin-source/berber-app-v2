import streamlit as st
import streamlit.components.v1 as components
import sqlite3
from datetime import datetime, timedelta


# ============================================================
# PODEŠAVANJE STRANICE
# ============================================================

st.set_page_config(
    page_title="Kod Kubanca",
    page_icon="✂️",
    layout="wide"
)


# ============================================================
# IZGLED
# ============================================================

st.markdown("""
<style>

.stApp {
    background-color: #1e1e1e;
    color: white;
}

.stMarkdown p {
    color: white !important;
}

h1, h2, h3, h4 {
    color: white !important;
}

.stButton > button {
    background-color: #2b2b2b;
    color: #d4af37;
    border: 2px solid #d4af37;
    border-radius: 10px;
    font-weight: 600;
}

.stButton > button:hover {
    background-color: #d4af37;
    color: black;
}

div[data-baseweb="input"] {
    background-color: #2b2b2b;
    border: 1px solid #d4af37;
    border-radius: 10px;
}

div[data-baseweb="select"] {
    background-color: #2b2b2b;
}

input {
    color: white !important;
    background-color: #2b2b2b !important;
}

[data-testid="stDateInput"] * {
    color: white !important;
}

div[data-testid="stMetric"] {
    background-color: #2b2b2b;
    border: 2px solid #d4af37;
    padding: 15px;
    border-radius: 15px;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: white !important;
}

div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
    color: white !important;
}

.admin-header {
    background-color: #2b2b2b;
    border: 1px solid #d4af37;
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 5px;
}

.admin-row {
    background-color: #252525;
    border-radius: 10px;
    padding: 8px 4px;
    margin-bottom: 6px;
}

.slot-free {
    background-color: #2e7d32;
    border-radius: 8px;
    padding: 8px;
    text-align: center;
    color: white;
    font-weight: bold;
}

.slot-busy {
    background-color: #c62828;
    border-radius: 8px;
    padding: 8px;
    text-align: center;
    color: white;
    font-weight: bold;
}

.pause-box {
    background-color: #444;
    border-radius: 8px;
    padding: 8px;
    text-align: center;
    color: #aaa;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# KONSTANTE
# ============================================================

DB_FILE = "termini.db"
DB_VERSION = 2

RADNO_VREME_PRE_PAUZE = ("09:00", "13:00")
RADNO_VREME_POSLE_PAUZE = ("14:00", "20:00")

PAUZA_POCETAK = "13:00"
PAUZA_KRAJ = "14:00"


# ============================================================
# BAZA
# ============================================================

def get_connection():
    return sqlite3.connect(DB_FILE)


def init_db():

    conn = get_connection()
    c = conn.cursor()

    # Tabela koja pamti verziju baze.
    c.execute("""
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute(
        "SELECT value FROM app_meta WHERE key='db_version'"
    )

    rezultat = c.fetchone()

    trenutna_verzija = int(rezultat[0]) if rezultat else 0

    # Ako je stara baza, jednom je očistimo.
    if trenutna_verzija != DB_VERSION:

        c.execute("DROP TABLE IF EXISTS rezervacije")
        c.execute("DROP TABLE IF EXISTS cenovnik")

        c.execute("""
            CREATE TABLE rezervacije (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usluga TEXT,
                datum TEXT NOT NULL,
                vreme TEXT NOT NULL,
                ime TEXT,
                telefon TEXT,
                cena INTEGER,
                status TEXT DEFAULT 'zakazan',
                payment_method TEXT
            )
        """)

        c.execute("""
            CREATE TABLE cenovnik (
                usluga TEXT PRIMARY KEY,
                cena INTEGER NOT NULL,
                trajanje INTEGER NOT NULL
            )
        """)

        usluge = [
            ("💇 Šišanje", 1500, 60),
            ("💇 Šišanje + pranje kose", 1900, 60),
            ("💇 Šišanje + brada", 2000, 60),
            ("💇 Šišanje + brada + pranje kose", 2400, 90),
            ("💇 Šišanje + brada + pranje kose + obrve", 2800, 90),
            ("🧔 Brada (samo)", 1000, 30),
            ("✨ Obrve (samo)", 400, 30)
        ]

        c.executemany("""
            INSERT INTO cenovnik
            (usluga, cena, trajanje)
            VALUES (?, ?, ?)
        """, usluge)

        c.execute("""
            INSERT OR REPLACE INTO app_meta
            (key, value)
            VALUES ('db_version', ?)
        """, (str(DB_VERSION),))

    conn.commit()
    conn.close()


# ============================================================
# DATUMI
# ============================================================

def formatiraj_datum(datum):
    if isinstance(datum, str):
        datum = datetime.strptime(datum, "%Y-%m-%d").date()

    return datum.strftime("%d.%m.%Y.")


def generisi_datume():
    danas = datetime.now().date()

    return [
        danas + timedelta(days=i)
        for i in range(7)
    ]


# ============================================================
# SLOTOVI
# ============================================================

def generisi_slotove_za_dan(datum):

    if isinstance(datum, str):
        datum_str = datum
    else:
        datum_str = datum.strftime("%Y-%m-%d")

    conn = get_connection()
    c = conn.cursor()

    trenutno = datetime.strptime("09:00", "%H:%M")
    kraj = datetime.strptime("20:00", "%H:%M")

    while trenutno < kraj:

        vreme = trenutno.strftime("%H:%M")

        # Pauza 13:00 - 14:00
        if "13:00" <= vreme < "14:00":
            trenutno += timedelta(minutes=30)
            continue

        c.execute("""
            SELECT id
            FROM rezervacije
            WHERE datum=? AND vreme=?
        """, (datum_str, vreme))

        postoji = c.fetchone()

        if not postoji:

            c.execute("""
                INSERT INTO rezervacije
                (datum, vreme, status)
                VALUES (?, ?, 'zakazan')
            """, (datum_str, vreme))

        trenutno += timedelta(minutes=30)

    conn.commit()
    conn.close()


def osvezi_termine():

    for datum in generisi_datume():
        generisi_slotove_za_dan(datum)


# ============================================================
# CENOVNIK
# ============================================================

def get_usluge():

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT usluga, cena, trajanje
        FROM cenovnik
        ORDER BY trajanje ASC, cena ASC
    """)

    usluge = c.fetchall()

    conn.close()

    return usluge


# ============================================================
# PROVERA SLOTOVA
# ============================================================

def proveri_slotove_za_uslugu(datum, vreme, trajanje):

    if isinstance(datum, str):
        datum_str = datum
    else:
        datum_str = datum.strftime("%Y-%m-%d")

    broj_slotova = trajanje // 30

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT vreme, ime
        FROM rezervacije
        WHERE datum=?
        ORDER BY vreme ASC
    """, (datum_str,))

    svi_slotovi = c.fetchall()

    conn.close()

    start_index = None

    for i, (slot_vreme, ime) in enumerate(svi_slotovi):

        if slot_vreme == vreme:
            start_index = i
            break

    if start_index is None:
        return None

    if start_index + broj_slotova > len(svi_slotovi):
        return None

    potrebni_slotovi = []

    prethodno_vreme = None

    for i in range(broj_slotova):

        slot_vreme, ime = svi_slotovi[start_index + i]

        # Mora biti slobodan.
        if ime is not None:
            return None

        # Slotovi moraju biti uzastopni.
        if prethodno_vreme:

            t1 = datetime.strptime(
                prethodno_vreme,
                "%H:%M"
            )

            t2 = datetime.strptime(
                slot_vreme,
                "%H:%M"
            )

            razlika = int(
                (t2 - t1).total_seconds() / 60
            )

            if razlika != 30:
                return None

        potrebni_slotovi.append(slot_vreme)

        prethodno_vreme = slot_vreme

    return potrebni_slotovi


# ============================================================
# REZERVACIJA
# ============================================================

def rezervisi_slotove(
    datum,
    slotovi,
    ime,
    telefon,
    usluga_ime,
    usluga_cena
):

    if isinstance(datum, str):
        datum_str = datum
    else:
        datum_str = datum.strftime("%Y-%m-%d")

    conn = get_connection()
    c = conn.cursor()

    try:

        # Još jedna provera neposredno pre upisa.
        placeholders = ",".join(["?"] * len(slotovi))

        c.execute(f"""
            SELECT id
            FROM rezervacije
            WHERE datum=?
            AND vreme IN ({placeholders})
            AND ime IS NOT NULL
        """, [datum_str] + slotovi)

        if c.fetchone():
            conn.rollback()
            conn.close()
            return False

        for index, slot_vreme in enumerate(slotovi):

            cena = usluga_cena if index == 0 else 0

            c.execute("""
                UPDATE rezervacije
                SET ime=?,
                    telefon=?,
                    usluga=?,
                    cena=?,
                    status='zakazan',
                    payment_method=NULL
                WHERE datum=?
                AND vreme=?
            """, (
                ime.strip(),
                telefon.strip(),
                usluga_ime,
                cena,
                datum_str,
                slot_vreme
            ))

        conn.commit()
        conn.close()

        return True

    except Exception:
        conn.rollback()
        conn.close()
        return False


# ============================================================
# OTKAZIVANJE
# ============================================================

def otkazi_termin(rezervacija_ids):

    if not isinstance(rezervacija_ids, list):
        rezervacija_ids = [rezervacija_ids]

    conn = get_connection()
    c = conn.cursor()

    placeholders = ",".join(["?"] * len(rezervacija_ids))

    c.execute(f"""
        UPDATE rezervacije
        SET ime=NULL,
            telefon=NULL,
            usluga=NULL,
            cena=NULL,
            status='zakazan',
            payment_method=NULL
        WHERE id IN ({placeholders})
    """, rezervacija_ids)

    conn.commit()
    conn.close()


# ============================================================
# NAPLATA
# ============================================================

def naplati_termin(rezervacija_ids, payment_method):

    if not isinstance(rezervacija_ids, list):
        rezervacija_ids = [rezervacija_ids]

    conn = get_connection()
    c = conn.cursor()

    placeholders = ",".join(["?"] * len(rezervacija_ids))

    c.execute(f"""
        UPDATE rezervacije
        SET status='naplacen',
            payment_method=?
        WHERE id IN ({placeholders})
    """, [payment_method] + rezervacija_ids)

    conn.commit()
    conn.close()


# ============================================================
# PROVERA DA LI JE TERMIN ZAVRŠEN
# ============================================================

def moze_naplata(datum, vremena):

    if isinstance(datum, str):
        datum_obj = datetime.strptime(
            datum,
            "%Y-%m-%d"
        ).date()
    else:
        datum_obj = datum

    danas = datetime.now().date()

    if datum_obj < danas:
        return True

    if datum_obj > danas:
        return False

    # Poslednji slot predstavlja početak poslednjeg
    # 30-minutnog slota.
    poslednji = max(vremena)

    pocetak = datetime.strptime(
        poslednji,
        "%H:%M"
    )

    kraj_usluge = (
        pocetak + timedelta(minutes=30)
    ).time()

    return datetime.now().time() >= kraj_usluge


# ============================================================
# ADMIN - BROJ KLIJENATA
# ============================================================

def get_unique_clients_count_for_date(datum):

    conn = get_connection()
    c = conn.cursor()

    datum_str = datum.strftime("%Y-%m-%d")

    c.execute("""
        SELECT COUNT(DISTINCT ime || '|' || telefon || '|' || usluga)
        FROM rezervacije
        WHERE datum=?
        AND ime IS NOT NULL
        AND status='zakazan'
    """, (datum_str,))

    rezultat = c.fetchone()

    conn.close()

    return rezultat[0] if rezultat else 0


def get_unique_clients_count_next_7_days():

    danas = datetime.now().date()
    kraj = danas + timedelta(days=6)

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT COUNT(DISTINCT ime || '|' || telefon || '|' || usluga)
        FROM rezervacije
        WHERE datum BETWEEN ? AND ?
        AND ime IS NOT NULL
        AND status='zakazan'
    """, (
        danas.strftime("%Y-%m-%d"),
        kraj.strftime("%Y-%m-%d")
    ))

    rezultat = c.fetchone()

    conn.close()

    return rezultat[0] if rezultat else 0


# ============================================================
# ADMIN - PAZAR
# ============================================================

def get_earnings_breakdown_for_date(datum):

    datum_str = (
        datum.strftime("%Y-%m-%d")
        if not isinstance(datum, str)
        else datum
    )

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT payment_method, SUM(cena)
        FROM rezervacije
        WHERE datum=?
        AND status='naplacen'
        AND cena > 0
        GROUP BY payment_method
    """, (datum_str,))

    rezultati = c.fetchall()

    conn.close()

    kes = 0
    kartica = 0

    for method, total in rezultati:

        if method == "Keš":
            kes = total or 0

        elif method == "Kartica":
            kartica = total or 0

    return kes + kartica, kes, kartica


def get_monthly_earnings_breakdown():

    danas = datetime.now().date()
    prvi_dan = danas.replace(day=1)

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT payment_method, SUM(cena)
        FROM rezervacije
        WHERE datum BETWEEN ? AND ?
        AND status='naplacen'
        AND cena > 0
        GROUP BY payment_method
    """, (
        prvi_dan.strftime("%Y-%m-%d"),
        danas.strftime("%Y-%m-%d")
    ))

    rezultati = c.fetchall()

    conn.close()

    kes = 0
    kartica = 0

    for method, total in rezultati:

        if method == "Keš":
            kes = total or 0

        elif method == "Kartica":
            kartica = total or 0

    return kes + kartica, kes, kartica


def get_yearly_earnings_breakdown():

    danas = datetime.now().date()
    prvi_dan = danas.replace(
        month=1,
        day=1
    )

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT payment_method, SUM(cena)
        FROM rezervacije
        WHERE datum BETWEEN ? AND ?
        AND status='naplacen'
        AND cena > 0
        GROUP BY payment_method
    """, (
        prvi_dan.strftime("%Y-%m-%d"),
        danas.strftime("%Y-%m-%d")
    ))

    rezultati = c.fetchall()

    conn.close()

    kes = 0
    kartica = 0

    for method, total in rezultati:

        if method == "Keš":
            kes = total or 0

        elif method == "Kartica":
            kartica = total or 0

    return kes + kartica, kes, kartica


# ============================================================
# KLIJENT - USLUGE
# ============================================================

def prikazi_usluge():

    usluge = get_usluge()

    st.write("### 💈 Korak 1: Odaberite uslugu")
    st.write("---")

    kolone = st.columns(2)

    for i, usluga in enumerate(usluge):

        ime_usluge, cena, trajanje = usluga

        with kolone[i % 2]:

            st.markdown(
                f"**{ime_usluge}**"
            )

            st.caption(
                f"{trajanje} min • {cena} din"
            )

            if st.button(
                "Izaberi",
                key=f"usluga_{i}",
                use_container_width=True
            ):

                st.session_state["izabrana_usluga"] = {
                    "ime": ime_usluge,
                    "cena": cena,
                    "trajanje": trajanje
                }

                st.session_state["izabrani_termin"] = None

                st.rerun()

            st.write("---")


# ============================================================
# KLIJENT - SLOTOVI
# ============================================================

def prikazi_slotove(datum):

    datum_str = datum.strftime("%Y-%m-%d")

    generisi_slotove_za_dan(datum)

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT vreme, ime
        FROM rezervacije
        WHERE datum=?
        ORDER BY vreme
    """, (datum_str,))

    slotovi = c.fetchall()

    conn.close()

    st.write("### ⏰ Korak 2: Odaberite vreme")

    for i in range(0, len(slotovi), 3):

        kolone = st.columns(3)

        for j in range(3):

            index = i + j

            if index >= len(slotovi):
                continue

            vreme, ime = slotovi[index]

            with kolone[j]:

                if vreme >= "13:00" and vreme < "14:00":

                    st.button(
                        "🚫 PAUZA",
                        disabled=True,
                        use_container_width=True,
                        key=f"pauza_{datum_str}_{vreme}"
                    )

                elif ime is not None:

                    st.button(
                        f"🔴 {vreme}",
                        disabled=True,
                        use_container_width=True,
                        key=f"zauzet_{datum_str}_{vreme}"
                    )

                else:

                    if st.button(
                        f"🟢 {vreme}",
                        key=f"slobodan_{datum_str}_{vreme}",
                        use_container_width=True
                    ):

                        st.session_state[
                            "izabrani_termin"
                        ] = vreme

                        st.rerun()


# ============================================================
# ADMIN - RUČNO ZAKAZIVANJE
# ============================================================

def admin_rucno_zakazi():

    with st.expander(
        "➕ Ručno zakazivanje",
        expanded=False
    ):

        with st.form("admin_zakazi_form"):

            ime = st.text_input(
                "Ime i prezime *"
            )

            telefon = st.text_input(
                "Telefon *"
            )

            datum = st.date_input(
                "Datum",
                value=datetime.now().date(),
                min_value=datetime.now().date()
            )

            usluge = get_usluge()

            opcije = [
                f"{u[0]} ({u[2]} min, {u[1]} din)"
                for u in usluge
            ]

            izabrana = st.selectbox(
                "Usluga",
                opcije
            )

            index = opcije.index(
                izabrana
            )

            usluga_ime = usluge[index][0]
            usluga_cena = usluge[index][1]
            usluga_trajanje = usluge[index][2]

            generisi_slotove_za_dan(datum)

            conn = get_connection()
            c = conn.cursor()

            c.execute("""
                SELECT vreme
                FROM rezervacije
                WHERE datum=?
                AND ime IS NULL
                ORDER BY vreme
            """, (
                datum.strftime("%Y-%m-%d"),
            ))

            slobodni = [
                r[0]
                for r in c.fetchall()
            ]

            conn.close()

            if slobodni:

                vreme = st.selectbox(
                    "Termin",
                    slobodni
                )

            else:

                vreme = None

                st.warning(
                    "Nema slobodnih termina."
                )

            potvrdi = st.form_submit_button(
                "✅ Zakaži",
                use_container_width=True
            )

            if potvrdi:

                if not ime.strip() or not telefon.strip():

                    st.warning(
                        "⚠️ Popunite ime i telefon."
                    )

                elif vreme is None:

                    st.error(
                        "Nema slobodnog termina."
                    )

                else:

                    slotovi = proveri_slotove_za_uslugu(
                        datum,
                        vreme,
                        usluga_trajanje
                    )

                    if slotovi is None:

                        st.error(
                            "❌ Nema dovoljno uzastopnih "
                            "slobodnih slotova."
                        )

                    else:

                        uspeh = rezervisi_slotove(
                            datum,
                            slotovi,
                            ime,
                            telefon,
                            usluga_ime,
                            usluga_cena
                        )

                        if uspeh:

                            st.success(
                                "✅ Termin je uspešno zakazan."
                            )

                            st.rerun()

                        else:

                            st.error(
                                "❌ Termin više nije slobodan."
                            )


# ============================================================
# ADMIN - UČITAVANJE GRUPISANIH REZERVACIJA
# ============================================================

def ucitaj_rezervacije_za_datum(datum):

    datum_str = (
        datum.strftime("%Y-%m-%d")
        if not isinstance(datum, str)
        else datum
    )

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT
            id,
            vreme,
            ime,
            telefon,
            usluga,
            cena,
            status,
            payment_method
        FROM rezervacije
        WHERE datum=?
        AND ime IS NOT NULL
        ORDER BY vreme ASC
    """, (datum_str,))

    rows = c.fetchall()

    conn.close()

    grupe = {}

    for (
        rezervacija_id,
        vreme,
        ime,
        telefon,
        usluga,
        cena,
        status,
        payment_method
    ) in rows:

        key = (
            ime,
            telefon,
            usluga
        )

        if key not in grupe:

            grupe[key] = {
                "ids": [],
                "vremena": [],
                "ime": ime,
                "telefon": telefon,
                "usluga": usluga,
                "cena": 0,
                "status": status,
                "payment_method": payment_method
            }

        grupe[key]["ids"].append(
            rezervacija_id
        )

        grupe[key]["vremena"].append(
            vreme
        )

        if cena and cena > 0:
            grupe[key]["cena"] = cena

        # Ako je bilo koji slot naplaćen,
        # cela grupa je naplaćena.
        if status == "naplacen":

            grupe[key]["status"] = "naplacen"

            if payment_method:
                grupe[key][
                    "payment_method"
                ] = payment_method

    return list(grupe.values())


# ============================================================
# ADMIN - TABELA
# ============================================================
@st.dialog("👤 Detalji termina")
def popup_zauzet_termin(
    podatak,
    ids,
    vremena,
    datum,
    vreme
):

    st.subheader("👤 Detalji klijenta")

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            f"**Ime:** {podatak['ime']}"
        )

        st.write(
            f"**Telefon:** {podatak['telefon']}"
        )

    with col2:

        st.write(
            f"**Usluga:** {podatak['usluga']}"
        )

        st.write(
            f"**Cena:** {podatak['cena']} din"
        )

    st.write(
        f"**Datum:** "
        f"{formatiraj_datum(datum)}"
    )

    st.write(
        f"**Vreme:** {vreme}"
    )

    st.markdown("---")

    # ====================================================
    # AKCIJE
    # ====================================================

    if podatak["status"] == "zakazan":

        a1, a2, a3 = st.columns(3)

        with a1:

            if st.button(
                "❌ Otkaži",
                key=f"popup_otkazi_{datum}_{vreme}",
                use_container_width=True
            ):

                otkazi_termin(ids)

                st.session_state[
                    "kalendar_klik"
                ] = None

                st.session_state[
                    "naplata_id"
                ] = None

                st.rerun()

        with a2:

            if st.button(
                "💰 Naplati",
                key=f"popup_naplati_{datum}_{vreme}",
                use_container_width=True
            ):

                st.session_state[
                    "naplata_id"
                ] = ids

                st.rerun()

        with a3:

            if st.button(
                "✖️ Zatvori",
                key=f"popup_zatvori_{datum}_{vreme}",
                use_container_width=True
            ):

                st.session_state[
                    "kalendar_klik"
                ] = None

                st.session_state[
                    "naplata_id"
                ] = None

                st.rerun()

    # ====================================================
    # NAPLATA
    # ====================================================

    if (
        st.session_state.get(
            "naplata_id"
        ) == ids
    ):

        st.markdown("---")

        st.write(
            f"💰 **Naplata: "
            f"{podatak['ime']} — "
            f"{podatak['cena']} din**"
        )

        izbor = st.radio(
            "Način plaćanja",
            ["Keš", "Kartica"],
            horizontal=True,
            key=f"popup_placanje_{datum}_{vreme}"
        )

        p1, p2 = st.columns(2)

        with p1:

            if st.button(
                "✅ Potvrdi naplatu",
                key=f"popup_potvrdi_{datum}_{vreme}",
                use_container_width=True
            ):

                if moze_naplata(
                    datum,
                    vremena
                ):

                    naplati_termin(
                        ids,
                        izbor
                    )

                    st.session_state[
                        "naplata_id"
                    ] = None

                    st.session_state[
                        "kalendar_klik"
                    ] = None

                    st.rerun()

                else:

                    st.warning(
                        "⏳ Termin još nije završen. "
                        "Naplata nije moguća pre "
                        "završetka usluge."
                    )

        with p2:

            if st.button(
                "Odustani",
                key=f"popup_odustani_{datum}_{vreme}",
                use_container_width=True
            ):

                st.session_state[
                    "naplata_id"
                ] = None

                st.rerun()

def prikaz_nedeljnog_kalendara(admin_datum):

    st.subheader("📅 Nedeljni pregled")

    # ----------------------------------------------------
    # SESSION STATE - KLIK NA SLOT
    # ----------------------------------------------------

    if "kalendar_klik" not in st.session_state:
        st.session_state["kalendar_klik"] = None

    klik = st.session_state.get(
        "kalendar_klik"
    )

    if klik is not None:

        if (
            not isinstance(klik, dict)
            or "tip" not in klik
            or "datum" not in klik
            or "vreme" not in klik
        ):

            st.session_state[
                "kalendar_klik"
            ] = None

            klik = None

    # ----------------------------------------------------
    # QUERY PARAMETRI
    # ----------------------------------------------------

    query_params = st.query_params

    akcija = query_params.get("akcija")
    datum_klik = query_params.get("datum")
    vreme_klik = query_params.get("vreme")
    tip_klik = query_params.get("tip")

    if (
        akcija == "klik"
        and datum_klik
        and vreme_klik
        and tip_klik
    ):

        st.session_state[
            "kalendar_klik"
        ] = {
            "tip": tip_klik,
            "datum": datum_klik,
            "vreme": vreme_klik
        }

        st.query_params.clear()

        st.rerun()

    # ----------------------------------------------------
    # DATUMI - NEDELJA
    # ----------------------------------------------------

    if isinstance(admin_datum, str):

        danas = datetime.strptime(
            admin_datum,
            "%Y-%m-%d"
        ).date()

    else:

        danas = admin_datum

    pocetak_nedelje = (
        danas
        - timedelta(
            days=danas.weekday()
        )
    )

    datumi = [
        pocetak_nedelje
        + timedelta(days=i)
        for i in range(7)
    ]

    # ----------------------------------------------------
    # REZERVACIJE IZ BAZE
    # ----------------------------------------------------

    conn = get_connection()
    c = conn.cursor()

    placeholders = ",".join(
        ["?"] * len(datumi)
    )

    datum_vrednosti = [
        d.strftime("%Y-%m-%d")
        for d in datumi
    ]

    c.execute(
        f"""
        SELECT
            id,
            datum,
            vreme,
            ime,
            telefon,
            usluga,
            cena,
            status,
            payment_method
        FROM rezervacije
        WHERE datum IN ({placeholders})
        AND ime IS NOT NULL
        ORDER BY datum, vreme
        """,
        datum_vrednosti
    )

    zauzeti = c.fetchall()

    conn.close()

    # ----------------------------------------------------
    # PODACI O TERMINIMA
    # ----------------------------------------------------

    podaci_termina = {}

    for row in zauzeti:

        (
            rezervacija_id,
            datum,
            vreme,
            ime,
            telefon,
            usluga,
            cena,
            status,
            payment_method
        ) = row

        podaci_termina[
            (datum, vreme)
        ] = {
            "id": rezervacija_id,
            "ime": ime,
            "telefon": telefon,
            "usluga": usluga,
            "cena": cena or 0,
            "status": status,
            "payment_method": payment_method
        }

    # ----------------------------------------------------
    # SLOTOVI
    # ----------------------------------------------------

    slotovi = []

    trenutno = datetime.strptime(
        "09:00",
        "%H:%M"
    )

    kraj = datetime.strptime(
        "20:00",
        "%H:%M"
    )

    while trenutno < kraj:

        vreme_str = trenutno.strftime(
            "%H:%M"
        )

        # PAUZA 13:00 - 14:00
        if "13:00" <= vreme_str < "14:00":

            trenutno += timedelta(
                minutes=30
            )

            continue

        slotovi.append(vreme_str)

        trenutno += timedelta(
            minutes=30
        )

    # ----------------------------------------------------
    # OZNAKE DANA
    # ----------------------------------------------------

    dani_oznake = [
        d.strftime("%a %d.")
        for d in datumi
    ]

    dani_vrednosti = [
        d.strftime("%Y-%m-%d")
        for d in datumi
    ]

    # ====================================================
    # HTML TABELA
    # ====================================================

    html = """
    <style>

        .kalendar-wrapper {
            overflow-x: auto;
            overflow-y: auto;
            max-height: 90vh;
            -webkit-overflow-scrolling: touch;
            margin: 10px 0;
            border: 1px solid #444;
            border-radius: 8px;
            background-color: #1e1e1e;
        }

        .kalendar-tabela {
            border-collapse: collapse;
            width: 100%;
            min-width: 600px;
            font-size: 14px;
            color: white;
        }

        .kalendar-tabela th,
        .kalendar-tabela td {
            padding: 4px 2px;
            text-align: center;
            border-bottom: 1px solid #333;
            border-right: 1px solid #333;
        }

        .kalendar-tabela th {
            background-color: #2b2b2b;
            color: #d4af37;
            font-weight: bold;
            position: sticky;
            top: 0;
            z-index: 10;
        }

        .vreme-kolona {
            background-color: #2b2b2b;
            font-weight: bold;
            color: #aaa;
            position: sticky;
            left: 0;
            z-index: 5;
            min-width: 45px;
            max-width: 45px;
            white-space: nowrap;
            padding: 2px 2px !important;
        }

        .slot-dugme {
            display: inline-block;
            width: 44px;
            height: 44px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            font-size: 0;
            padding: 0;
            margin: 0 auto;
            transition: transform 0.1s;
        }

        .slot-dugme:active {
            transform: scale(0.92);
        }

        .slot-slobodan {
            background-color: #2e7d32;
        }

        .slot-slobodan:hover {
            background-color: #43a047;
        }

        .slot-zauzet {
            background-color: #c62828;
        }

        .slot-zauzet:hover {
            background-color: #e53935;
        }

        .dan-kolona {
            min-width: 64px;
        }

        .kalendar-wrapper::-webkit-scrollbar {
            height: 6px;
            width: 6px;
        }

        .kalendar-wrapper::-webkit-scrollbar-track {
            background: #2b2b2b;
        }

        .kalendar-wrapper::-webkit-scrollbar-thumb {
            background: #d4af37;
            border-radius: 3px;
        }

    </style>

    <script>

        function klikniSlot(
    tip,
    datum,
    vreme
) {

    window.parent.location.search =
        `?akcija=klik&tip=${tip}&datum=${datum}&vreme=${vreme}`;

}

    </script>

    <div class="kalendar-wrapper">

    <table class="kalendar-tabela">

        <thead>

            <tr>

                <th class="vreme-kolona">
                    Vreme
                </th>
    """

    for oznaka in dani_oznake:

        html += (
            f"<th class='dan-kolona'>"
            f"{oznaka}"
            f"</th>"
        )

    html += """
            </tr>

        </thead>

        <tbody>
    """

    # ----------------------------------------------------
    # REDOVI TABELЕ
    # ----------------------------------------------------

    for slot in slotovi:

        html += (
            f"<tr>"
            f"<td class='vreme-kolona'>"
            f"{slot}"
            f"</td>"
        )

        for datum in dani_vrednosti:

            key = (
                datum,
                slot
            )

            if key in podaci_termina:

                # ----------------------------------------
                # ZAUZET - CRVENO
                # ----------------------------------------

                html += f"""
                    <td class="dan-kolona">

                        <button class='slot-dugme slot-zauzet'
                                onclick="klikniSlot('zauzet', '{datum}', '{slot}')">
                        </button>

                    </td>
                """

            else:

                # ----------------------------------------
                # SLOBODAN - ZELENO
                # ----------------------------------------

                html += f"""
                    <td class="dan-kolona">

                        <button class='slot-dugme slot-slobodan'
                                onclick="klikniSlot('slobodan', '{datum}', '{slot}')">
                        </button>

                    </td>
                """

        html += "</tr>"

    html += """
        </tbody>

    </table>

    </div>
    """

    # ----------------------------------------------------
    # PRIKAZ TABELE
    # ----------------------------------------------------

    components.html(
        html,
        height=600,
        scrolling=False
    )

    # ====================================================
    # OBRADA KLIKA
    # ====================================================

    klik = st.session_state.get(
        "kalendar_klik"
    )

    if not klik:
        return

    tip = klik["tip"]
    datum = klik["datum"]
    vreme = klik["vreme"]

    # ====================================================
    # SLOBODAN TERMIN
    # ====================================================

    if tip == "slobodan":

        st.divider()

        st.subheader(
            "🟢 Novi termin"
        )

        st.write(
            f"**Datum:** "
            f"{formatiraj_datum(datum)}"
        )

        st.write(
            f"**Vreme:** {vreme}"
        )

        with st.form(
            key=f"novi_termin_{datum}_{vreme}"
        ):

            ime = st.text_input(
                "Ime i prezime *"
            )

            telefon = st.text_input(
                "Telefon *"
            )

            conn = get_connection()
            c = conn.cursor()

            c.execute("""
                SELECT
                    usluga,
                    cena,
                    trajanje
                FROM cenovnik
                ORDER BY trajanje ASC
            """)

            usluge = c.fetchall()

            conn.close()

            usluga_opcije = [
                f"{u[0]} ({u[2]} min, {u[1]} din)"
                for u in usluge
            ]

            izabrana = st.selectbox(
                "Usluga",
                usluga_opcije
            )

            idx = usluga_opcije.index(
                izabrana
            )

            usluga_ime = usluge[idx][0]
            usluga_cena = usluge[idx][1]
            usluga_trajanje = usluge[idx][2]

            potvrdi = st.form_submit_button(
                "✅ Zakaži",
                use_container_width=True
            )

            if potvrdi:

                if (
                    not ime.strip()
                    or not telefon.strip()
                ):

                    st.warning(
                        "⚠️ Popunite ime i telefon."
                    )

                else:

                    slotovi_za_uslugu = (
                        proveri_slotove_za_uslugu(
                            datum,
                            vreme,
                            usluga_trajanje
                        )
                    )

                    if slotovi_za_uslugu is None:

                        st.error(
                            "❌ Nema dovoljno "
                            "slobodnih termina."
                        )

                    else:

                        uspeh = rezervisi_slotove(
                            datum,
                            slotovi_za_uslugu,
                            ime,
                            telefon,
                            usluga_ime,
                            usluga_cena
                        )

                        if uspeh:

                            st.session_state[
                                "kalendar_klik"
                            ] = None

                            st.rerun()

                        else:

                            st.error(
                                "❌ Greška pri rezervaciji."
                            )

        if st.button(
            "✖️ Odustani",
            key=f"odustani_slobodan_{datum}_{vreme}",
            use_container_width=True
        ):

            st.session_state[
                "kalendar_klik"
            ] = None

            st.rerun()

        return
# ====================================================
# ZAUZET TERMIN
# ====================================================

podatak = podaci_termina.get(
    (datum, vreme)
)

if podatak is None:

    st.warning(
        "Podaci za ovaj termin "
        "nisu pronađeni."
    )

    st.session_state[
        "kalendar_klik"
    ] = None

    return

st.divider()

st.subheader(
    "👤 Detalji klijenta"
)

col1, col2 = st.columns(2)

with col1:

    st.write(
        f"**Ime:** {podatak['ime']}"
    )

    st.write(
        f"**Telefon:** {podatak['telefon']}"
    )

with col2:

    st.write(
        f"**Usluga:** {podatak['usluga']}"
    )

    st.write(
        f"**Cena:** {podatak['cena']} din"
    )

# ====================================================
# PRONAĐI SVE SLOTOVE ISTE REZERVACIJE
# ====================================================

ids = []

vremena = []

for (d, v), p in podaci_termina.items():

        if (
            d == datum
            and p["ime"] == podatak["ime"]
            and p["telefon"] == podatak["telefon"]
            and p["usluga"] == podatak["usluga"]
        ):

            ids.append(
                p["id"]
            )

            vremena.append(v)

    ids = sorted(
        set(ids)
    )

    vremena = sorted(
        set(vremena)
    )
    popup_zauzet_termin(
    podatak,
    ids,
    vremena,
    datum,
    vreme
    )

   

    # ====================================================
    # VEĆ NAPLAĆENO
    # ====================================================

    elif podatak["status"] == "naplacen":

        st.success(
            f"✅ Naplaćeno — "
            f"{podatak['payment_method']}"
        )

        if st.button(
            "✖️ Zatvori",
            key=f"zatvori_naplaceno_{datum}_{vreme}",
            use_container_width=True
        ):

            st.session_state[
                "kalendar_klik"
            ] = None

            st.rerun()


# ============================================================
# INICIJALIZACIJA
# ============================================================

init_db()
osvezi_termine()


# ============================================================
# SESSION STATE
# ============================================================

if "izabrana_usluga" not in st.session_state:
    st.session_state[
        "izabrana_usluga"
    ] = None

if "izabrani_termin" not in st.session_state:
    st.session_state[
        "izabrani_termin"
    ] = None

if "booking_success" not in st.session_state:
    st.session_state[
        "booking_success"
    ] = False

if "booking_details" not in st.session_state:
    st.session_state[
        "booking_details"
    ] = None

if "admin_authenticated" not in st.session_state:
    st.session_state[
        "admin_authenticated"
    ] = False

if "admin_password" not in st.session_state:
    st.session_state[
        "admin_password"
    ] = "admin123"

if "naplata_id" not in st.session_state:
    st.session_state[
        "naplata_id"
    ] = None


# ============================================================
# TABOVI
# ============================================================

tab1, tab2 = st.tabs(
    ["📅 Zakazivanje", "🔑 Admin Panel"]
)


# ============================================================
# TAB 1 - KLIJENT
# ============================================================

with tab1:

    if st.session_state["booking_success"]:

        detalji = st.session_state[
            "booking_details"
        ]

        st.success(
            "✅ Uspešno ste zakazali termin!"
        )

        st.markdown(f"""
        <div style="
            background-color:#2b2b2b;
            padding:20px;
            border-radius:15px;
            border:2px solid #d4af37;
            margin-top:15px;
        ">

        <h2 style="color:#d4af37 !important;">
        ✂️ Termin je zakazan
        </h2>

        <p><b>Klijent:</b> {detalji["ime"]}</p>

        <p><b>Usluga:</b> {detalji["usluga"]}</p>

        <p><b>Datum:</b>
        {formatiraj_datum(detalji["datum"])}</p>

        <p><b>Vreme:</b>
        {detalji["vreme"]}</p>

        <p><b>Trajanje:</b>
        {detalji["trajanje"]} min</p>

        <p><b>Cena:</b>
        {detalji["cena"]} din</p>

        </div>
        """, unsafe_allow_html=True)

        if st.button(
            "📅 Zakaži novi termin",
            use_container_width=True
        ):

            st.session_state[
                "booking_success"
            ] = False

            st.session_state[
                "izabrana_usluga"
            ] = None

            st.session_state[
                "izabrani_termin"
            ] = None

            st.rerun()

    else:

        datumi = generisi_datume()

        datum = st.selectbox(
            "📅 Datum",
            datumi,
            format_func=formatiraj_datum,
            key="klijent_datum"
        )

        st.info(
            f"📅 Termini za "
            f"{formatiraj_datum(datum)}"
        )

        prikazi_usluge()

        if st.session_state[
            "izabrana_usluga"
        ] is not None:

            prikazi_slotove(datum)

        if st.session_state[
            "izabrani_termin"
        ] is not None:

            termin = st.session_state[
                "izabrani_termin"
            ]

            usluga = st.session_state[
                "izabrana_usluga"
            ]

            st.write(
                "### 📝 Korak 3: Unesite podatke"
            )

            slotovi = proveri_slotove_za_uslugu(
                datum,
                termin,
                usluga["trajanje"]
            )

            if slotovi is None:

                st.error(
                    "❌ Ovaj termin više nije "
                    "dostupan."
                )

                st.session_state[
                    "izabrani_termin"
                ] = None

            else:

                with st.form(
                    "klijent_form"
                ):

                    ime = st.text_input(
                        "Ime i prezime *"
                    )

                    telefon = st.text_input(
                        "Telefon *"
                    )

                    st.write(
                        f"**Usluga:** "
                        f"{usluga['ime']}"
                    )

                    st.write(
                        f"**Vreme:** "
                        f"{termin}"
                    )

                    st.write(
                        f"**Trajanje:** "
                        f"{usluga['trajanje']} min"
                    )

                    st.write(
                        f"**Cena:** "
                        f"{usluga['cena']} din"
                    )

                    potvrdi = st.form_submit_button(
                        "✅ Zakaži termin",
                        use_container_width=True
                    )

                    if potvrdi:

                        if (
                            not ime.strip()
                            or not telefon.strip()
                        ):

                            st.warning(
                                "⚠️ Popunite ime "
                                "i telefon."
                            )

                        else:

                            # Provera neposredno pre upisa.
                            provereni_slotovi = (
                                proveri_slotove_za_uslugu(
                                    datum,
                                    termin,
                                    usluga["trajanje"]
                                )
                            )

                            if provereni_slotovi is None:

                                st.error(
                                    "❌ Termin je "
                                    "u međuvremenu zauzet."
                                )

                            else:

                                uspeh = rezervisi_slotove(
                                    datum,
                                    provereni_slotovi,
                                    ime,
                                    telefon,
                                    usluga["ime"],
                                    usluga["cena"]
                                )

                                if uspeh:

                                    st.session_state[
                                        "booking_success"
                                    ] = True

                                    st.session_state[
                                        "booking_details"
                                    ] = {
                                        "ime": ime,
                                        "usluga": usluga["ime"],
                                        "datum": datum,
                                        "vreme": termin,
                                        "trajanje": usluga["trajanje"],
                                        "cena": usluga["cena"]
                                    }

                                    st.session_state[
                                        "izabrana_usluga"
                                    ] = None

                                    st.session_state[
                                        "izabrani_termin"
                                    ] = None

                                    st.rerun()

                                else:

                                    st.error(
                                        "❌ Greška pri "
                                        "rezervaciji."
                                    )


# ============================================================
# TAB 2 - ADMIN
# ============================================================

with tab2:

    if not st.session_state[
        "admin_authenticated"
    ]:

        st.write("### 🔐 Admin pristup")

        password = st.text_input(
            "Unesite lozinku",
            type="password"
        )

        if st.button(
            "Potvrdi",
            use_container_width=True
        ):

            if password == st.session_state[
                "admin_password"
            ]:

                st.session_state[
                    "admin_authenticated"
                ] = True

                st.rerun()

            else:

                st.error(
                    "❌ Pogrešna lozinka."
                )

    else:

        st.success(
            "🔓 Admin panel"
        )

        # ----------------------------------------------------
        # PROMENA LOZINKE
        # ----------------------------------------------------

        with st.expander(
            "🔑 Promeni lozinku"
        ):

            old = st.text_input(
                "Stara lozinka",
                type="password",
                key="old_pass"
            )

            new = st.text_input(
                "Nova lozinka",
                type="password",
                key="new_pass"
            )

            confirm = st.text_input(
                "Potvrdi novu lozinku",
                type="password",
                key="confirm_pass"
            )

            if st.button(
                "Promeni lozinku"
            ):

                if old != st.session_state[
                    "admin_password"
                ]:

                    st.error(
                        "Stara lozinka nije tačna."
                    )

                elif not new or new != confirm:

                    st.error(
                        "Nove lozinke se ne "
                        "poklapaju."
                    )

                else:

                    st.session_state[
                        "admin_password"
                    ] = new

                    st.success(
                        "Lozinka je promenjena."
                    )

        # ----------------------------------------------------
        # RUČNO ZAKAZIVANJE
        # ----------------------------------------------------

        admin_rucno_zakazi()

        st.markdown("---")

        # ----------------------------------------------------
        # DATUM
        # ----------------------------------------------------

        st.write(
            "## 📅 Pregled termina"
        )

        admin_datumi = generisi_datume()

        admin_datum = st.selectbox(
            "Izaberite datum",
            admin_datumi,
            format_func=formatiraj_datum,
            key="admin_datum"
        )

        # ----------------------------------------------------
        # METRIKE
        # ----------------------------------------------------

        st.markdown("---")

        st.write(
            f"## 📊 Finansijski pregled — "
            f"{formatiraj_datum(admin_datum)}"
        )

        m1, m2 = st.columns(2)

        with m1:

            st.metric(
                "📅 Zakazano danas",
                get_unique_clients_count_for_date(
                    admin_datum
                )
            )

        with m2:

            st.metric(
                "📆 Narednih 7 dana",
                get_unique_clients_count_next_7_days()
            )

        p1, p2 = st.columns(2)

        with p1:

            uk, ke, ka = (
                get_monthly_earnings_breakdown()
            )

            st.write("### 💰 Mesečni pazar")

            st.write(
                f"Keš: **{ke:,.0f} din**"
            )

            st.write(
                f"Kartica: **{ka:,.0f} din**"
            )

            st.write(
                f"Ukupno: **{uk:,.0f} din**"
            )

        with p2:

            uk, ke, ka = (
                get_yearly_earnings_breakdown()
            )

            st.write("### 📈 Godišnji pazar")

            st.write(
                f"Keš: **{ke:,.0f} din**"
            )

            st.write(
                f"Kartica: **{ka:,.0f} din**"
            )

            st.write(
                f"Ukupno: **{uk:,.0f} din**"
            )

        # ----------------------------------------------------
        # DNEVNI PAZAR
        # ----------------------------------------------------

        st.markdown("---")

        ukupno, kes, kartica = (
            get_earnings_breakdown_for_date(
                admin_datum
            )
        )

        st.markdown(f"""
        <div style="
            background-color:#1e1e1e;
            padding:20px;
            border-radius:12px;
            border:2px solid #d4af37;
            text-align:center;
        ">

        <h3 style="color:#d4af37 !important;">
        💵 Pazar za {formatiraj_datum(admin_datum)}
        </h3>

        <p>
        Keš: <b>{kes:,.0f} din</b>
        &nbsp;&nbsp;&nbsp;
        Kartica: <b>{kartica:,.0f} din</b>
        </p>

        <h2 style="color:#d4af37 !important;">
        Ukupno: {ukupno:,.0f} din
        </h2>

        </div>
        """, unsafe_allow_html=True)

        # ----------------------------------------------------
        # TABELA
        # ----------------------------------------------------

        st.markdown("---")

        st.write(
            f"## 📋 Termini za "
            f"{formatiraj_datum(admin_datum)}"
        )

        prikaz_nedeljnog_kalendara(
    admin_datum

        )
