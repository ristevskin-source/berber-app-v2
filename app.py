import streamlit as st
import sqlite3
from datetime import datetime, timedelta

# --- PODEŠAVANJE STRANICE ---
st.set_page_config(page_title="Kod Kubanca", page_icon="✂️")

# --- INICIJALIZACIJA BAZE ---
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
        cena INTEGER,
        status TEXT DEFAULT 'zakazan',
        payment_method TEXT
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

    # Dodajemo kolone ako ne postoje (za stare baze)
    try:
        c.execute("ALTER TABLE rezervacije ADD COLUMN status TEXT DEFAULT 'zakazan'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE rezervacije ADD COLUMN payment_method TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

# --- FUNKCIJE ZA GENERISANJE SLOTOVA ---
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
                (usluga, datum, vreme, ime, telefon, cena, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (None, datum, vreme, None, None, None, 'zakazan')
            )

        trenutno += timedelta(minutes=15)

    conn.commit()
    conn.close()

# --- POMOĆNE FUNKCIJE ---
def formatiraj_datum(datum):
    return datum.strftime("%d.%m.%Y.")

def generisi_datume():
    danas = datetime.now().date()
    datumi = []
    for i in range(0, 14):  # Generiše termine za narednih 14 dana
        datumi.append(danas + timedelta(days=i))
    return datumi

def osvezi_termine():
    datumi = generisi_datume()

    for datum in datumi:
        generisi_slotove_za_dan(datum)

# --- FUNKCIJE ZA REZERVACIJE ---
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
                SET ime=?, telefon=?, usluga=?, cena=?, status='zakazan'
                WHERE datum=? AND vreme=?
            """, (ime, telefon, usluga_ime, usluga_cena, datum, slot_vreme))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        st.error(e)
        return False

# --- ADMIN FUNKCIJE ZA METRIKE I AKCIJE ---
def get_today_bookings_count():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM rezervacije WHERE datum=? AND ime IS NOT NULL", (datetime.now().date(),))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_next_7_days_bookings_count():
    today = datetime.now().date()
    end_date = today + timedelta(days=6)
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM rezervacije WHERE datum BETWEEN ? AND ? AND ime IS NOT NULL", (today, end_date))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_monthly_earnings_breakdown():
    today = datetime.now().date()
    first_day = today.replace(day=1)
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("""
        SELECT payment_method, SUM(cena) 
        FROM rezervacije 
        WHERE datum BETWEEN ? AND ? AND status='naplacen'
        GROUP BY payment_method
    """, (first_day, today))
    results = c.fetchall()
    conn.close()
    
    kes = 0
    kartica = 0
    for method, total in results:
        if method == 'Keš':
            kes = total if total else 0
        elif method == 'Kartica':
            kartica = total if total else 0
    ukupno = kes + kartica
    return ukupno, kes, kartica

def get_yearly_earnings_breakdown():
    today = datetime.now().date()
    first_day = today.replace(month=1, day=1)
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("""
        SELECT payment_method, SUM(cena) 
        FROM rezervacije 
        WHERE datum BETWEEN ? AND ? AND status='naplacen'
        GROUP BY payment_method
    """, (first_day, today))
    results = c.fetchall()
    conn.close()
    
    kes = 0
    kartica = 0
    for method, total in results:
        if method == 'Keš':
            kes = total if total else 0
        elif method == 'Kartica':
            kartica = total if total else 0
    ukupno = kes + kartica
    return ukupno, kes, kartica

def get_today_earnings_breakdown():
    today = datetime.now().date()
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("""
        SELECT payment_method, SUM(cena) 
        FROM rezervacije 
        WHERE datum=? AND status='naplacen'
        GROUP BY payment_method
    """, (today,))
    results = c.fetchall()
    conn.close()
    
    kes = 0
    kartica = 0
    for method, total in results:
        if method == 'Keš':
            kes = total if total else 0
        elif method == 'Kartica':
            kartica = total if total else 0
    ukupno = kes + kartica
    return ukupno, kes, kartica

def otkazi_termin(rezervacija_id):
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("""
        UPDATE rezervacije 
        SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, status='otkazan', payment_method=NULL
        WHERE id=?
    """, (rezervacija_id,))
    conn.commit()
    conn.close()

def naplati_termin(rezervacija_id, payment_method):
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("UPDATE rezervacije SET status='naplacen', payment_method=? WHERE id=?", (payment_method, rezervacija_id))
    conn.commit()
    conn.close()

# --- FUNKCIJA ZA PRIKAZ USLUGA (2 kolone za mobilni) ---
def prikazi_usluge():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("SELECT usluga, cena, trajanje FROM cenovnik ORDER BY trajanje ASC")
    usluge = c.fetchall()
    conn.close()

    st.write("### 💈 Korak 1: Odaberite uslugu")
    st.write("---")
    
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

# --- FUNKCIJA ZA PRIKAZ SLOTOVA ---
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

# --- ADMINISTRATORSKA FUNKCIJA (ručno zakazivanje) ---
def admin_rucno_zakazi(datum):
    st.write("### ➕ Ručno zakazivanje")
    
    with st.form(key="admin_zakazi_form"):
        ime = st.text_input("Ime i prezime *")
        telefon = st.text_input("Telefon *")
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

# ===================================================================
# GLAVNI DEO APLIKACIJE
# ===================================================================

init_db()

if 'izabrana_usluga' not in st.session_state:
    st.session_state['izabrana_usluga'] = None
if 'izabrani_termin' not in st.session_state:
    st.session_state['izabrani_termin'] = None
if 'booking_success' not in st.session_state:
    st.session_state['booking_success'] = False
if 'admin_authenticated' not in st.session_state:
    st.session_state['admin_authenticated'] = False
if 'admin_password' not in st.session_state:
    st.session_state['admin_password'] = 'admin123'
if 'naplata_id' not in st.session_state:
    st.session_state['naplata_id'] = None

st.image("IMG-c75b1bbded411581450ad9e3374dbc68-V.jpg", width=300)

tab1, tab2 = st.tabs(["📅 Zakazivanje", "🔑 Admin Panel"])

# ============================================================
# TAB 1: ZAKAZIVANJE (klijentski deo)
# ============================================================
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

# ============================================================
# TAB 2: ADMIN PANEL
# ============================================================
with tab2:
    if not st.session_state['admin_authenticated']:
        st.write("### 🔐 Admin pristup")
        password = st.text_input("Unesite lozinku", type="password")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Potvrdi"):
                if password == st.session_state['admin_password']:
                    st.session_state['admin_authenticated'] = True
                    st.rerun()
                else:
                    st.error("Pogrešna lozinka!")
    else:
        with st.expander("🔑 Promeni lozinku"):
            st.write("Promena lozinke (samo za admina)")
            old = st.text_input("Stara lozinka", type="password", key="old_pass")
            new = st.text_input("Nova lozinka", type="password", key="new_pass")
            confirm = st.text_input("Potvrdi novu lozinku", type="password", key="confirm_pass")
            if st.button("Promeni lozinku"):
                if old == st.session_state['admin_password']:
                    if new and new == confirm:
                        st.session_state['admin_password'] = new
                        st.success("Lozinka uspešno promenjena!")
                    else:
                        st.error("Nove lozinke se ne poklapaju ili su prazne")
                else:
                    st.error("Stara lozinka nije tačna")

        admin_rucno_zakazi(datetime.now().date())
        
        st.write("---")
        st.write("## 📊 Finansijski pregled")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📅 Zakazano danas", get_today_bookings_count())
        with col2:
            st.metric("📆 Zakazano u narednih 7 dana", get_next_7_days_bookings_count())
        
        col3, col4 = st.columns(2)
        with col3:
            st.write("**💰 Mesečni pazar**")
            uk, ke, ka = get_monthly_earnings_breakdown()
            st.write(f"Keš: {ke:,.0f} din")
            st.write(f"Kartica: {ka:,.0f} din")
            st.write(f"**Ukupno: {uk:,.0f} din**")
        with col4:
            st.write("**📈 Godišnji pazar**")
            uk, ke, ka = get_yearly_earnings_breakdown()
            st.write(f"Keš: {ke:,.0f} din")
            st.write(f"Kartica: {ka:,.0f} din")
            st.write(f"**Ukupno: {uk:,.0f} din**")
        
        # --- Dnevni pazar (odvojeno keš, kartica, ukupno) ---
        st.markdown("---")
        ukupno, kes, kartica = get_today_earnings_breakdown()
        st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border: 2px solid #d4af37; text-align: center;">
            <h3 style="color: #d4af37;">💵 Dnevni pazar (do sada)</h3>
            <div style="display: flex; justify-content: space-around; flex-wrap: wrap; margin-top: 10px;">
                <div><span style="color: #aaa;">Keš:</span> <strong>{kes:,.0f} din</strong></div>
                <div><span style="color: #aaa;">Kartica:</span> <strong>{kartica:,.0f} din</strong></div>
                <div><span style="color: #d4af37;">Ukupno:</span> <strong style="font-size: 1.4em;">{ukupno:,.0f} din</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("---")
        st.write("## 📋 Termini za danas")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("""
            SELECT id, vreme, ime, telefon, usluga, cena, status, payment_method
            FROM rezervacije
            WHERE datum=?
            AND ime IS NOT NULL
            ORDER BY vreme ASC
        """, (datetime.now().date(),))
        rows = c.fetchall()
        conn.close()
        
        if rows:
            for idx, row in enumerate(rows):
                id, vreme, ime, telefon, usluga, cena, status, payment_method = row
                with st.container():
                    cols = st.columns([1.2, 1.5, 1.2, 2, 1.2, 1.5])
                    with cols[0]:
                        st.write(vreme)
                    with cols[1]:
                        st.write(ime)
                    with cols[2]:
                        st.write(telefon)
                    with cols[3]:
                        st.write(f"{usluga} ({cena} din)")
                    with cols[4]:
                        if status == 'zakazan':
                            if st.button("❌ Otkaži", key=f"otkazi_{id}"):
                                otkazi_termin(id)
                                st.rerun()
                            if st.button("💰 Naplati", key=f"naplati_{id}"):
                                st.session_state['naplata_id'] = id
                                st.rerun()
                        elif status == 'naplacen':
                            st.success(f"✅ Naplaćeno ({payment_method})")
                        elif status == 'otkazan':
                            st.warning("❌ Otkazano")
                    with cols[5]:
                        if status == 'zakazan' and st.session_state.get('naplata_id') == id:
                            payment_choice = st.radio(
                                "Način plaćanja",
                                ["Keš", "Kartica"],
                                key=f"payment_{id}",
                                label_visibility="collapsed"
                            )
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("✅ Potvrdi", key=f"potvrdi_{id}"):
                                    naplati_termin(id, payment_choice)
                                    st.session_state['naplata_id'] = None
                                    st.rerun()
                            with col_b:
                                if st.button("❌ Odustani", key=f"odustani_{id}"):
                                    st.session_state['naplata_id'] = None
                                    st.rerun()
                    st.markdown("---")
        else:
            st.info("Nema zakazanih klijenata za danas.")
