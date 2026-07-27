import streamlit as st
import sqlite3
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="💈 Berberski salon - Zakazivanje", layout="centered")

RADNO_VREME = [(9,0), (20,0)]
INTERVAL_MIN = 15
BROJ_DANA = 7
PAUZA_POCETAK = 12
PAUZA_KRAJ = 13

def init_db():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS rezervacije 
                 (id INTEGER PRIMARY KEY, usluga TEXT, datum TEXT, vreme TEXT, 
                  ime TEXT, telefon TEXT, cena INTEGER, naplaceno INTEGER DEFAULT 0, datum_naplate TEXT)''')
    
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
    c.executemany("INSERT OR IGNORE INTO cenovnik (usluga, cena, trajanje) VALUES (?, ?, ?)", usluge)
    
    c.execute('''CREATE TABLE IF NOT EXISTS konfiguracija (lozinka TEXT)''')
    c.execute("SELECT * FROM konfiguracija")
    if not c.fetchone():
        c.execute("INSERT INTO konfiguracija (lozinka) VALUES ('1234')")
    
    c.execute('''CREATE TABLE IF NOT EXISTS pauze 
                 (id INTEGER PRIMARY KEY, datum TEXT, vreme TEXT, napomena TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

def formatiraj_datum(datum_str):
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    dani_u_nedelji = ["Ponedeljak", "Utorak", "Sreda", "Četvrtak", "Petak", "Subota", "Nedelja"]
    return f"{dani_u_nedelji[dan.weekday()]}, {dan.strftime('%d.%m.%Y')}"

def generisi_datume():
    now = datetime.now()
    if now.hour >= 20:
        start = now + timedelta(days=1)
    else:
        start = now
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    datumi = []
    for i in range(BROJ_DANA):
        dan = start + timedelta(days=i)
        if dan.weekday() != 6:
            datumi.append(dan.strftime("%Y-%m-%d"))
    return datumi

def generisi_slotove_za_dan(datum_str):
    dan = datetime.strptime(datum_str, "%Y-%m-%d")
    if dan.weekday() == 6:
        return
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute("DELETE FROM rezervacije WHERE datum=? AND ime IS NULL", (datum_str,))
    
    sat_start, min_start = RADNO_VREME[0]
    sat_kraj, min_kraj = RADNO_VREME[1]
    trenutno = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_start, minute=min_start)
    kraj = datetime.strptime(datum_str, "%Y-%m-%d").replace(hour=sat_kraj, minute=min_kraj)
    
    c.execute("SELECT vreme FROM pauze WHERE datum=?", (datum_str,))
    pauze = [row[0] for row in c.fetchall()]
    for i in range(PAUZA_POCETAK*4, PAUZA_KRAJ*4):
        vreme = f"{i//4:02d}:{(i%4)*15:02d}"
        if vreme not in pauze:
            pauze.append(vreme)
    
    slotovi = []
    while trenutno < kraj:
        vreme = trenutno.strftime("%H:%M")
        if vreme not in pauze:
            slotovi.append((None, datum_str, vreme, None, None, None, 0, None))
        trenutno += timedelta(minutes=INTERVAL_MIN)
    
    if slotovi:
        c.executemany("INSERT INTO rezervacije (usluga, datum, vreme, ime, telefon, cena, naplaceno, datum_naplate) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", slotovi)
        conn.commit()
    conn.close()

def osvezi_termine():
    datumi = generisi_datume()
    for d in datumi:
        generisi_slotove_za_dan(d)
    return True

def proveri_slotove_za_uslugu(datum, pocetak, trajanje):
    broj_slotova = trajanje // INTERVAL_MIN
    if trajanje % INTERVAL_MIN != 0:
        broj_slotova += 1
    
    pocetak_dt = datetime.strptime(pocetak, "%H:%M")
    kraj_dt = pocetak_dt + timedelta(minutes=trajanje)
    
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute("""
        SELECT vreme FROM rezervacije 
        WHERE datum=? AND vreme >= ? AND vreme < ? AND ime IS NOT NULL AND ime != ''
    """, (datum, pocetak, kraj_dt.strftime("%H:%M")))
    zauzeti = c.fetchall()
    conn.close()
    
    if zauzeti:
        return None
    
    slotovi = []
    trenutno = pocetak_dt
    while trenutno < kraj_dt:
        slotovi.append(trenutno.strftime("%H:%M"))
        trenutno += timedelta(minutes=INTERVAL_MIN)
    
    return slotovi

def rezervisi_slotove(datum, slotovi, ime, telefon, usluga, cena, trajanje):
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    for vreme in slotovi:
        c.execute("""
            UPDATE rezervacije 
            SET ime=?, telefon=?, usluga=?, cena=?, naplaceno=0 
            WHERE datum=? AND vreme=?
        """, (ime, telefon, usluga, cena, datum, vreme))
    
    conn.commit()
    conn.close()
    return True

def prikazi_usluge():
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    c.execute("SELECT usluga, cena, trajanje FROM cenovnik ORDER BY trajanje ASC")
    usluge = c.fetchall()
    conn.close()
    
    st.write("### ✂️ Korak 1: Izaberite uslugu")
    
    for usluga, cena, trajanje in usluge:
        col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
        with col1:
            st.write(f"**{usluga}**")
        with col2:
            st.write(f"{trajanje} min")
        with col3:
            st.write(f"{cena} din")
        with col4:
            if st.button("Izaberi", key=f"usluga_{usluga}"):
                st.session_state['izabrana_usluga'] = {
                    'ime': usluga,
                    'cena': cena,
                    'trajanje': trajanje
                }
                if 'izabrani_termin' in st.session_state:
                    del st.session_state['izabrani_termin']
                st.rerun()
        st.write("---")
    
    if 'izabrana_usluga' in st.session_state and isinstance(st.session_state['izabrana_usluga'], dict):
        usl = st.session_state['izabrana_usluga']
        st.success(f"✅ Izabrali ste: **{usl['ime']}** ({usl['trajanje']} min, {usl['cena']} din)")

def prikazi_slotove(datum):
    """Prikazuje tabelu slotova sa mogućnošću izbora"""
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute("""
        SELECT vreme, ime FROM rezervacije 
        WHERE datum=? 
        ORDER BY vreme ASC
    """, (datum,))
    svi_slotovi = c.fetchall()
    conn.close()
    
    if not svi_slotovi:
        st.warning("⏳ Nema termina za izabrani datum.")
        return
    
    st.write("### 📅 Korak 2: Izaberite termin")
    
    cols_per_row = 4
    rows = [svi_slotovi[i:i+cols_per_row] for i in range(0, len(svi_slotovi), cols_per_row)]
    
    for row in rows:
        cols = st.columns(cols_per_row)
        for j, (vreme, ime) in enumerate(row):
            with cols[j]:
                if ime is None or ime == "":
                    if st.button(f"🟢 {vreme}", key=f"slot_{datum}_{vreme}", use_container_width=True):
                        st.session_state['izabrani_termin'] = vreme
                        st.rerun()
                else:
                    st.markdown(f"""
                    <div style="background-color:#7a2a2a; color:#aaaaaa; border:1px solid #aa4a4a; border-radius:8px; padding:8px 0; text-align:center; width:100%; font-weight:bold; cursor:not-allowed; opacity:0.7;">
                        🔴 {vreme}
                    </div>
                    """, unsafe_allow_html=True)

def prikazi_admin_tabelu(datum):
    conn = sqlite3.connect('termini.db')
    c = conn.cursor()
    
    c.execute("""
        SELECT vreme, ime, telefon, usluga, cena, naplaceno FROM rezervacije 
        WHERE datum=? 
        ORDER BY vreme ASC
    """, (datum,))
    svi_slotovi = c.fetchall()
    conn.close()
    
    if not svi_slotovi:
        st.info("📭 Nema termina za izabrani datum.")
        return
    
    st.write("### 📋 Raspored termina")
    
    cols = st.columns([2, 3, 3, 4, 3, 2])
    with cols[0]: st.write("**Vreme**")
    with cols[1]: st.write("**Klijent**")
    with cols[2]: st.write("**Telefon**")
    with cols[3]: st.write("**Usluga**")
    with cols[4]: st.write("**Cena**")
    with cols[5]: st.write("**Status**")
    
    st.write("---")
    
    for vreme, ime, telefon, usluga, cena, naplaceno in svi_slotovi:
        cols = st.columns([2, 3, 3, 4, 3, 2])
        with cols[0]: st.write(vreme)
        with cols[1]: st.write(ime if ime else "")
        with cols[2]: st.write(telefon if telefon else "")
        with cols[3]: st.write(usluga if usluga else "")
        with cols[4]: st.write(f"{cena} din" if cena else "")
        with cols[5]:
            if ime:
                if naplaceno == 1:
                    st.write("✅ Naplaćeno")
                else:
                    st.write("⏳ Nenaplaćeno")
            else:
                st.write("🟢 Slobodno")

def admin_rucno_zakazi(datum):
    st.write("### ➕ Ručno zakazivanje")
    
    with st.form(key="admin_zakazi_form"):
        ime = st.text_input("Ime i prezime *")
        telefon = st.text_input("Telefon *")
        
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

# ---------- UI ----------
st.title("💈 Berberski salon - Zakazivanje")

# Inicijalizacija session_state
if 'izabrana_usluga' not in st.session_state:
    st.session_state['izabrana_usluga'] = None
if 'izabrani_termin' not in st.session_state:
    st.session_state['izabrani_termin'] = None
if 'booking_success' not in st.session_state:
    st.session_state['booking_success'] = False

tab1, tab2 = st.tabs(["📅 Zakazivanje", "🔑 Admin Panel"])

with tab1:
    # Resetuj session_state ako je u neispravnom stanju
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
                            if st.button("🔄 Izaberi drugi termin"):
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

with tab2:
    if "admin" not in st.session_state:
        st.session_state.admin = False
    
    if not st.session_state.admin:
        lozinka = st.text_input("Lozinka:", type="password")
        if lozinka == "1234":
            st.session_state.admin = True
            st.rerun()
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Očisti sve termine (reset)"):
                conn = sqlite3.connect('termini.db')
                c = conn.cursor()
                c.execute("UPDATE rezervacije SET ime=NULL, telefon=NULL, usluga=NULL, cena=NULL, naplaceno=0")
                conn.commit()
                conn.close()
                st.success("✅ Svi termini su očišćeni!")
                st.rerun()
        with col2:
            if st.button("🔄 Ručno generiši slotove"):
                if osvezi_termine():
                    st.success("✅ Slotovi su regenerisani!")
                    st.rerun()
                else:
                    st.error("❌ Greška pri generisanju slotova.")
                    st.rerun()
        
        st.divider()
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        
        c.execute("""
            SELECT COUNT(DISTINCT ime || '|' || telefon || '|' || datum || '|' || usluga) 
            FROM rezervacije 
            WHERE datum=? AND ime IS NOT NULL
        """, (today,))
        danas_klijenata = c.fetchone()[0] or 0
        
        c.execute("SELECT COUNT(*) FROM rezervacije WHERE ime IS NOT NULL AND (naplaceno IS NULL OR naplaceno=0)")
        nenaplaceno = c.fetchone()[0] or 0
        
        conn.close()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📅 Danas", f"{danas_klijenata} klijenata")
        with col2:
            st.metric("⏳ Nenaplaćeni slotovi", f"{nenaplaceno}")
        
        st.subheader("📊 Finansijski izveštaj")
        
        this_month = datetime.now().strftime("%Y-%m")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate=?", (today,))
        danas_promet = c.fetchone()[0] or 0
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate LIKE ?", (f"{this_month}%",))
        mesec_promet = c.fetchone()[0] or 0
        
        c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1")
        ukupno_promet = c.fetchone()[0] or 0
        
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📅 Danas", f"{danas_promet} din")
        with col2:
            st.metric("📆 Ovaj mesec", f"{mesec_promet} din")
        with col3:
            st.metric("💰 Ukupno", f"{ukupno_promet} din")
        
        st.subheader("📈 Promet po mesecima")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT substr(datum_naplate,1,7) FROM rezervacije WHERE naplaceno=1 AND datum_naplate IS NOT NULL ORDER BY datum_naplate DESC")
        dostupni_meseci = [row[0] for row in c.fetchall()]
        conn.close()
        
        if dostupni_meseci:
            izabrani_mesec = st.selectbox("Izaberite mesec", dostupni_meseci, index=0)
            
            conn = sqlite3.connect('termini.db')
            c = conn.cursor()
            c.execute("SELECT sum(cena) FROM rezervacije WHERE naplaceno=1 AND datum_naplate LIKE ?", (f"{izabrani_mesec}%",))
            promet_mesec = c.fetchone()[0] or 0
            conn.close()
            
            st.write(f"### Promet za {izabrani_mesec}: **{promet_mesec} din**")
        else:
            st.info("📭 Još uvek nema naplaćenih usluga.")
        
        # ---------- ADMIN TABELA ----------
        st.subheader("📋 Pregled i upravljanje terminima")
        
        conn = sqlite3.connect('termini.db')
        c = conn.cursor()
        datumi_raw = generisi_datume()
        conn.close()
        
        if datumi_raw:
            admin_datum = st.selectbox(
                "Izaberite datum za pregled",
                datumi_raw,
                format_func=formatiraj_datum,
                key="admin_datum"
            )
            
            prikazi_admin_tabelu(admin_datum)
            
            st.divider()
            
            admin_rucno_zakazi(admin_datum)
        else:
            st.info("📭 Nema dostupnih datuma.")
