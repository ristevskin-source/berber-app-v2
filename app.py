import streamlit as st
import sqlite3
from datetime import datetime, timedelta

# --- PODEŠAVANJE STRANICE ---
st.set_page_config(page_title="Kod Kubanca", page_icon="✂️")

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
    pass # Mesto za logiku ako ti treba osvežavanje

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
                SET ime=?, telefon=?, usluga=?, cena=?, trajanje=?
                WHERE datum=? AND vreme=?
            """, (ime, telefon, usluga_ime, usluga_cena, usluga_trajanje, datum, slot_vreme))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
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
    c.execute("SELECT vreme, ime FROM rezervacije WHERE datum=? ORDER BY vreme ASC", (datum,))
    svi_slotovi = c.fetchall()
    conn.close()
    
    if not svi_slotovi:
        st.caption("Nema dostupnih termina za ovaj datum.")
        return

    st.write("### ⏰ Korak 2: Odaberite vreme")
    
    # Pravimo 3 kolone (Streamlit će ih na telefonu spakovati najbolje što može)
    cols = st.columns(3)

    for i, (vreme, ime) in enumerate(svi_slotovi):
        with cols[i % 3]: # Raspoređuje ih u 3 kolone redom
            
            # 1. PAUZA - Zabrana ulaska
            if vreme >= "12:00" and vreme < "13:00":
                st.markdown(
                    f"""
                    <div style="background-color: #333333; border: 1px solid #ff4b4b; border-radius: 8px; padding: 6px 0; text-align: center; margin-bottom: 8px; font-size: 12px;">
                        <span style="color: #ff4b4b; font-weight: bold;">🚫 PAUZA</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                continue

            # 2. ZAUZETI TERMIN
            if ime is not None:
                st.markdown(
                    f"""
                    <div style="background-color: #a85a5a; border-radius: 8px; padding: 6px 0; text-align: center; margin-bottom: 8px; font-size: 13px;">
                        <span style="color: #ffffff; font-weight: bold;">{vreme}</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            else:
                # 3. SLOBODNI TERMIN
                if st.button(f"🟢 {vreme}", key=f"slot_{vreme}_{datum}"):
                    st.session_state['izabrani_termin'] = vreme
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
