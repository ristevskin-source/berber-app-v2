import streamlit as st
import sqlite3
from datetime import datetime, timedelta

# --- PODEŠAVANJE STRANICE ---
st.set_page_config(page_title="Kod Kubanca", page_icon="✂️")
def init_db():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS rezervacije (
        id INTEGER PRIMARY KEY,
        usluga TEXT,
        datum TEXT,
        vreme TEXT,
        ime TEXT,
        telefon TEXT,
        cena INTEGER
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS cenovnik (
        usluga TEXT PRIMARY KEY,
        cena INTEGER,
        trajanje INTEGER
    )''')

    usluge = [
        ('💇 Šišanje', 1500, 45),
        ('💇 Šišanje + pranje kose', 1900, 60),
        ('💇 Šišanje + brada', 2000, 60),
        ('💇 Šišanje + brada + pranje kose', 2400, 75),
        ('💇 Šišanje + brada + pranje kose + obrve', 2800, 90),
        ('🧔 Brada (samo)', 1000, 30),
        ('✨ Obrve (samo)', 400, 15)
    ]

    c.executemany(
        "INSERT OR IGNORE INTO cenovnik (usluga, cena, trajanje) VALUES (?, ?, ?)",
        usluge
    )

    conn.commit()
    conn.close()


init_db()
osvezi_termine()
def generisi_slotove_za_dan(datum):
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()

    pocetak = datetime.strptime(f"{datum} 09:00", "%Y-%m-%d %H:%M")
    kraj = datetime.strptime(f"{datum} 20:00", "%Y-%m-%d %H:%M")

    trenutno = pocetak

    while trenutno < kraj:
        vreme = trenutno.strftime("%H:%M")

        c.execute(
            "SELECT * FROM rezervacije WHERE datum=? AND vreme=?",
            (datum, vreme)
        )

        postoji = c.fetchone()

        if not postoji:
            c.execute(
                """INSERT INTO rezervacije 
                (usluga, datum, vreme, ime, telefon, cena)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (None, datum, vreme, None, None, None)
            )

        trenutno += timedelta(minutes=15)

    conn.commit()
    conn.close()

# --- PRIKAZ LOGOA (Zameni "logo.png" sa tačnim imenom tvoje slike) ---
st.image("IMG-c75b1bbded411581450ad9e3374dbc68-V.jpg", width=300)

# --- POMOĆNE FUNKCIJE ---
def formatiraj_datum(datum):
    return datum.strftime("%d.%m.%Y.")

def generisi_datume():
    danas = datetime.now().date()
    datumi = []
    for i in range(0, 14): # Generiše termine za narednih 14 dana
        datumi.append(danas + timedelta(days=i))
    return datumi

def osvezi_termine():
    datumi = generisi_datume()

    for datum in datumi:
        generisi_slotove_za_dan(datum)
# --- GLAVNE FUNKCIJE ---
def proveri_slotove_za_uslugu(datum, vreme, trajanje):
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()

    c.execute("SELECT vreme, ime FROM rezervacije WHERE datum=? ORDER BY vreme ASC", (datum,))
    svi_slotovi = c.fetchall()
    conn.close()

    start_index = None
    for i, (slot_vreme, ime) in enumerate(svi_slotovi):
        if slot_vreme == vreme:
            start_index = i
            break

    if start_index is None:
        return None

    broj_slotova = trajanje // 15
    if start_index + broj_slotova > len(svi_slotovi):
        return None

    potrebni_slotovi = []
    for i in range(broj_slotova):
        slot_vreme, ime = svi_slotovi[start_index + i]
        if ime is not None:
            return None
        potrebni_slotovi.append(slot_vreme)

    return potrebni_slotovi

def rezervisi_slotove(datum, slotovi, ime, telefon, usluga_ime, usluga_cena, usluga_trajanje):
    try:
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()

        for slot_vreme in slotovi:
            c.execute("""
                UPDATE rezervacije 
                SET ime=?, telefon=?, usluga=?, cena=?
                WHERE datum=? AND vreme=?
            """, (ime, telefon, usluga_ime, usluga_cena, datum, slot_vreme))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        st.error(e)
        return False

# --- FUNKCIJA ZA PRIKAZ USLUGA (2 kolone za mobilni) ---
def prikazi_usluge():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("SELECT usluga, cena, trajanje FROM cenovnik ORDER BY trajanje ASC")
    usluge = c.fetchall()
    conn.close()

    st.write("### 💈 Korak 1: Odaberite uslugu")
    st.write("---")
    
    # Podela na 2 kolone za bolji prikaz na mobilnom
    cols = st.columns(2)
    
    for i, u in enumerate(usluge):
        with cols[i % 2]:
            ime_usluge, cena, trajanje = u
            st.markdown(f"**{ime_usluge}**")
            st.caption(f"{trajanje} min • {cena} din")
            
            if st.button(f"Izaberi", key=f"usl_{i}"):
                st.session_state['izabrana_usluga'] = {
                    'ime': ime_usluge,
                    'cena': cena,
                    'trajanje': trajanje
                }
                st.session_state['izabrani_termin'] = None
                st.rerun()
            st.write("---")

# --- FUNKCIJA ZA PRIKAZ SLOTOVA (HTML Mreža za mobilni) ---
def prikazi_slotove(datum):

    conn = sqlite3.connect('termini.db')
    c = conn.cursor()

    c.execute(
        "SELECT vreme, ime FROM rezervacije WHERE datum=? ORDER BY vreme ASC",
        (datum,)
    )

    svi_slotovi = c.fetchall()
    conn.close()

    if not svi_slotovi:
        st.caption("Nema dostupnih termina za ovaj datum.")
        return

    st.write("### ⏰ Korak 2: Odaberite vreme")

    red = []

    for vreme, ime in svi_slotovi:

        if "12:00" <= vreme < "13:00":
            red.append("PAUZA")
        elif ime is not None:
            red.append(f"🔴 {vreme}")
        else:
            red.append(vreme)


    for i in range(0, len(red), 3):

        kolone = st.columns(3)

        for j in range(3):

            index = i + j

            if index < len(red):

                termin = red[index]

                with kolone[j]:

                    if termin == "PAUZA":

                        st.button(
                            "🚫 PAUZA",
                            disabled=True,
                            use_container_width=True,
                            key=f"pauza_{i}_{j}"
                        )

                    elif termin.startswith("🔴"):

                        st.button(
                            termin,
                            disabled=True,
                            use_container_width=True,
                            key=f"zauzet_{termin}"
                        )

                    else:

                        if st.button(
                            f"🟢 {termin}",
                            key=f"slot_{termin}_{datum}",
                            use_container_width=True
                        ):
                            st.session_state['izabrani_termin'] = termin
                            st.rerun()
# --- ADMINISTRATORSKA FUNKCIJA (sa datumom) ---
def admin_rucno_zakazi(datum):
    st.write("### ➕ Ručno zakazivanje")
    
    with st.form(key="admin_zakazi_form"):
        ime = st.text_input("Ime i prezime *")
        telefon = st.text_input("Telefon *")
        
        # DODATAK: Odabir datuma unutar forme
        datum = st.date_input("Odaberi datum za uslugu", value=datetime.now().date())
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT usluga, cena, trajanje FROM cenovnik ORDER BY trajanje ASC")
        usluge = c.fetchall()
        conn.close()
        
        usluga_opcije = [f"{u[0]} ({u[2]} min, {u[1]} din)" for u in usluge]
        izabrana = st.selectbox("Usluga", usluga_opcije)
        
        idx = usluga_opcije.index(izabrana) if izabrana in usluga_opcije else 0
        usluga_ime = usluge[idx][0]
        usluga_cena = usluge[idx][1]
        usluga_trajanje = usluge[idx][2]
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("""
            SELECT vreme, ime FROM rezervacije 
            WHERE datum=? AND ime IS NULL
            ORDER BY vreme ASC
        """, (datum,))
        slobodni_slotovi = c.fetchall()
        conn.close()
        
        if not slobodni_slotovi:
            st.warning("Nema slobodnih termina za izabrani datum.")
            return
        
        vreme_opcije = [v[0] for v in slobodni_slotovi]
        izabrano_vreme = st.selectbox("Termin", vreme_opcije)
        
        potvrdi = st.form_submit_button("✅ Zakaži za klijenta")
        
        if potvrdi:
            if ime and telefon and ime.strip() and telefon.strip():
                slotovi = proveri_slotove_za_uslugu(datum, izabrano_vreme, usluga_trajanje)
                if slotovi is None:
                    st.error("❌ Nema dovoljno slobodnih termina za ovu uslugu u izabrano vreme.")
                else:
                    if rezervisi_slotove(datum, slotovi, ime, telefon, usluga_ime, usluga_cena, usluga_trajanje):
                        st.success(f"✅ Uspešno zakazano: {ime} - {usluga_ime} u {izabrano_vreme}")
                        st.rerun()
                    else:
                        st.error("❌ Greška pri rezervaciji.")
            else:
                st.warning("⚠️ Popunite ime i telefon.")

# --- GLAVNI DEO APLIKACIJE ---

# Inicijalizacija session_state
if 'izabrana_usluga' not in st.session_state:
    st.session_state['izabrana_usluga'] = None
if 'izabrani_termin' not in st.session_state:
    st.session_state['izabrani_termin'] = None
if 'booking_success' not in st.session_state:
    st.session_state['booking_success'] = False

tab1, tab2 = st.tabs(["📅 Zakazivanje", "🔑 Admin Panel"])

with tab1:
    if 'izabrana_usluga' in st.session_state and not isinstance(st.session_state['izabrana_usluga'], (dict, type(None))):
        st.session_state['izabrana_usluga'] = None

    if st.session_state['booking_success']:
        detalji = st.session_state['booking_details']
        st.balloons()
        st.markdown(f"""
        <div style="background-color: #3a3a3a; padding: 20px; border-radius: 15px; border-left: 6px solid #d4af37; box-shadow: 0 4px 12px rgba(0,0,0,0.5); margin: 20px 0;">
            <h2 style="color: #d4af37; margin:0;">✅ Uspešno ste zakazali!</h2>
            <p><strong>Usluga:</strong> {detalji['usluga']}</p>
            <p><strong>Datum:</strong> {formatiraj_datum(detalji['datum'])}</p>
            <p><strong>Vreme:</strong> {detalji['vreme']}</p>
            <p><strong>Trajanje:</strong> {detalji['trajanje']} min</p>
            <p><strong>Cena:</strong> {detalji['cena']} din</p>
            <p><strong>Klijent:</strong> {detalji['ime']}</p>
            <p style="margin-top:15px; font-size:1.2em; color:#d4af37;">✂️ Vidimo se!</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📅 Zakaži novi termin"):
            st.session_state['booking_success'] = False
            st.session_state['izabrana_usluga'] = None
            st.session_state['izabrani_termin'] = None
            st.rerun()
    else:
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        datumi_raw = generisi_datume()
        conn.close()
        
        if datumi_raw:
            osvezi_termine()
            
            datum = st.selectbox("Datum", datumi_raw, format_func=formatiraj_datum)
            st.info(f"📅 Termini za: {formatiraj_datum(datum)}")
            
            prikazi_usluge()
            
            if st.session_state['izabrana_usluga'] is not None:
                prikazi_slotove(datum)
                
                if st.session_state['izabrani_termin'] is not None:
                    kliknuto_vreme = st.session_state['izabrani_termin']
                    st.write("### 📝 Korak 3: Unesite podatke")
                    
                    with st.form(key="klijent_form"):
                        ime = st.text_input("Ime i prezime *")
                        telefon = st.text_input("Telefon *")
                        
                        usluga = st.session_state['izabrana_usluga']
                        slotovi = proveri_slotove_za_uslugu(datum, kliknuto_vreme, usluga['trajanje'])
                        
                        if slotovi is None:
                           st.error("❌ Nema dovoljno slobodnih termina za ovu uslugu u izabrano vreme.")

                        

                        if odustani:
                          st.session_state['izabrani_termin'] = None
                          st.rerun()
                        else:
                            st.success(f"✅ Usluga **{usluga['ime']}** traje **{usluga['trajanje']} min** i zauzima **{len(slotovi)} slotova**.")
                            st.write("Zauzeće sledeće slotove:")
                            for s in slotovi:
                                st.markdown(f"- 🔴 {s}")
                            
                            potvrdi = st.form_submit_button("✅ Zakaži")
                            
                            if potvrdi:
                                if ime and telefon and ime.strip() and telefon.strip():
                                    slotovi = proveri_slotove_za_uslugu(datum, kliknuto_vreme, usluga['trajanje'])
                                    if slotovi is None:
                                        st.error("❌ Nažalost, neko je već zauzeo neki od ovih slotova. Molimo izaberite drugi termin.")
                                        st.session_state['izabrani_termin'] = None
                                        st.rerun()
                                    else:
                                        if rezervisi_slotove(datum, slotovi, ime, telefon, usluga['ime'], usluga['cena'], usluga['trajanje']):
                                            st.session_state['izabrani_termin'] = None
                                            st.session_state['izabrana_usluga'] = None
                                            st.session_state['booking_success'] = True
                                            st.session_state['booking_details'] = {
                                                'usluga': usluga['ime'],
                                                'datum': datum,
                                                'vreme': kliknuto_vreme,
                                                'trajanje': usluga['trajanje'],
                                                'cena': usluga['cena'],
                                                'ime': ime
                                            }
                                            st.rerun()
                                        else:
                                            st.error("❌ Greška pri rezervaciji.")
                                else:
                                    st.warning("⚠️ Popunite ime i telefon.")
        else:
            st.error("❌ Nema dostupnih datuma.")

# --- ADMIN TAB ---
with tab2:
    st.write("## 🔑 Admin Panel")
    admin_rucno_zakazi(datetime.now().date())

    st.write("---")
    st.write("### 📋 Zakazani klijenti")

    conn = sqlite3.connect('termini.db')
    c = conn.cursor()

    c.execute("""
        SELECT vreme, ime, telefon, usluga, cena
        FROM rezervacije
        WHERE datum=?
        AND ime IS NOT NULL
        ORDER BY vreme ASC
    """, (datetime.now().date(),))

    zakazani = c.fetchall()
    conn.close()

    if zakazani:
        st.table(zakazani)
    else:
        st.info("Nema zakazanih klijenata za danas.")
