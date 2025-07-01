# ✅ VERSION FONCTIONNELLE avec st.rerun() corrigé pour le Gantt

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import plotly.express as px

st.set_page_config(page_title="🛠️ Calcul du Temps de Montage", layout="wide")
st.title("🔧 Estimation du Temps de Montage")

# --- Fonctions Utilitaires ---
def trouver_disponibilite(date_jour, h_debut_jour, h_fin_jour, planning, temps_requis):
    debut_jour = datetime.combine(date_jour, h_debut_jour)
    fin_jour = datetime.combine(date_jour, h_fin_jour)
    temps_requis_td = timedelta(minutes=temps_requis)
    taches = []
    for _, row in planning.iterrows():
        if pd.to_datetime(row["date"]).date() == date_jour:
            try:
                debut_tache = datetime.combine(date_jour, datetime.strptime(row["heure_debut"], "%H:%M").time())
                fin_tache = datetime.combine(date_jour, datetime.strptime(row["heure_fin"], "%H:%M").time())
                taches.append((debut_tache, fin_tache))
            except ValueError:
                continue
    taches.sort()
    plages_libres = []
    cursor = debut_jour
    for debut_tache, fin_tache in taches:
        if cursor < debut_tache:
            plages_libres.append((cursor, debut_tache))
        cursor = max(cursor, fin_tache)
    if cursor < fin_jour:
        plages_libres.append((cursor, fin_jour))
    for debut, fin in plages_libres:
        if fin - debut >= temps_requis_td:
            return debut, debut + temps_requis_td
    return None, None

def trouver_prochaine_dispo(temps_total_minutes):
    if not st.session_state.admin_planning:
        return None, None
    planning_df = pd.DataFrame(st.session_state.admin_planning, columns=["date", "heure_debut", "heure_fin", "nom"])
    planning_df["date"] = pd.to_datetime(planning_df["date"]).dt.date
    date_actuelle = datetime.today().date()
    for i in range(30):
        jour = date_actuelle + timedelta(days=i)
        debut, fin = trouver_disponibilite(jour, time(8, 0), time(17, 0), planning_df, temps_total_minutes)
        if debut and fin:
            return debut, fin
    return None, None

def afficher_gantt(planning):
    if not planning:
        st.warning("Aucune donnée à afficher dans le Gantt.")
        return
    df = pd.DataFrame(planning, columns=["date", "heure_debut", "heure_fin", "nom"])
    df["Début"] = pd.to_datetime(df["date"] + " " + df["heure_debut"], errors='coerce')
    df["Fin"] = pd.to_datetime(df["date"] + " " + df["heure_fin"], errors='coerce')
    df.dropna(subset=["Début", "Fin"], inplace=True)
    if df.empty:
        st.warning("Aucune donnée valide pour le Gantt.")
        return
    df["Jour"] = pd.to_datetime(df["date"]).dt.strftime("%A %d/%m")
    df["Tâche"] = df["nom"]
    fig = px.timeline(df, x_start="Début", x_end="Fin", y="Jour", color="Tâche", title="📅 Planning Gantt")
    fig.update_yaxes(autorange="reversed", title="Jour")
    fig.update_xaxes(tickformat="%H:%M", dtick=3600000)
    fig.update_layout(height=600, title_font_size=22)
    st.plotly_chart(fig, use_container_width=True)

def calculer_temps(commande_df, base_df):
    total = 0
    erreurs = []
    commande_df.columns = commande_df.columns.str.strip().str.lower().str.replace(' ', '').str.replace('\ufeff', '')
    base_df.columns = base_df.columns.str.strip().str.lower().str.replace(' ', '').str.replace('\ufeff', '')
    if 'reference' not in commande_df.columns or 'quantite' not in commande_df.columns:
        erreurs.append("Colonnes manquantes dans la commande")
        return 0, erreurs
    if 'reference' not in base_df.columns or 'temps_montage' not in base_df.columns:
        erreurs.append("Colonnes manquantes dans la base")
        return 0, erreurs
    commande_df['reference'] = commande_df['reference'].astype(str).str.strip().str.upper()
    base_df['reference'] = base_df['reference'].astype(str).str.strip().str.upper()
    commande_df = commande_df.dropna(subset=['reference'])
    commande_df = commande_df[commande_df['reference'].str.strip() != '']
    try:
        commande_df['quantite'] = pd.to_numeric(commande_df['quantite'], errors='coerce').fillna(0).astype(int)
    except Exception as e:
        erreurs.append(f"Quantité invalide : {e}")
        return 0, erreurs
    df_merge = commande_df.merge(base_df[['reference', 'temps_montage']], on='reference', how='left')
    df_merge['temps_total'] = df_merge['quantite'] * df_merge['temps_montage']
    total = df_merge['temps_total'].sum()
    missing = df_merge[df_merge['temps_montage'].isna()]['reference'].unique()
    for ref in missing:
        erreurs.append(f"Référence manquante : {ref}")
    return int(total), erreurs

# --- Initialisation ---
if 'admin_planning' not in st.session_state:
    st.session_state.admin_planning = []
if 'commande_df' not in st.session_state:
    st.session_state.commande_df = pd.DataFrame()
if 'commande_validee' not in st.session_state:
    st.session_state.commande_validee = False
if 'derniere_dispo' not in st.session_state:
    st.session_state.derniere_dispo = None
if 'nom_tache_user' not in st.session_state:
    st.session_state.nom_tache_user = "Montage client"

# --- Interface ---
role = st.sidebar.radio("👤 Choisissez votre rôle :", ["Utilisateur", "Administrateur"])

if role == "Administrateur":
    if st.sidebar.text_input("🔐 Mot de passe :", type="password") != "safran123":
        st.warning("Mot de passe incorrect.")
        st.stop()
    st.header("📋 Gestion Planning")
    date = st.date_input("Date", datetime.today())
    h1, h2 = st.columns(2)
    hd = h1.time_input("Heure début", time(8, 0))
    hf = h2.time_input("Heure fin", time(17, 0))
    with st.form("admin_form"):
        c1, c2, c3 = st.columns([1, 1, 2])
        d = c1.time_input("Début", time(9, 0))
        f = c2.time_input("Fin", time(10, 0))
        nom = c3.text_input("Nom", "Tâche")
        if st.form_submit_button("Ajouter"):
            if d >= f:
                st.error("Heures invalides")
            else:
                st.session_state.admin_planning.append((str(date), d.strftime("%H:%M"), f.strftime("%H:%M"), nom))
                st.rerun()
    if st.session_state.admin_planning:
        st.subheader("📄 Planning")
        afficher_gantt(st.session_state.admin_planning)
        if st.button("🚼 Vider"):
            st.session_state.admin_planning = []
            st.rerun()

else:
    base = pd.read_csv("Test_1.csv")
    base.columns = base.columns.str.strip().str.lower().str.replace(' ', '')
    base['temps_montage'] = pd.to_numeric(base['temps_montage'], errors='coerce').fillna(0).astype(int)
    uploaded = st.file_uploader("Commande CSV", type="csv")
    if uploaded:
        st.session_state.commande_df = pd.read_csv(uploaded)
        st.session_state.commande_validee = False
        st.dataframe(st.session_state.commande_df)

    if not st.session_state.commande_df.empty and not st.session_state.commande_validee:
        if st.button("⏱️ Calculer"):
            total, erreurs = calculer_temps(st.session_state.commande_df, base)
            if total > 0:
                debut, fin = trouver_prochaine_dispo(total)
                if debut and fin:
                    st.session_state.derniere_dispo = (debut, fin)
                    st.session_state.commande_validee = True
                    st.session_state.temps_total = total
                    st.rerun()
            if erreurs:
                st.warning("\n".join(erreurs))

    if st.session_state.commande_validee and st.session_state.derniere_dispo:
        debut, fin = st.session_state.derniere_dispo
        heures = st.session_state.temps_total // 60
        minutes = st.session_state.temps_total % 60
        st.success(f"Disponible : {debut.strftime('%A %d/%m/%Y %H:%M')} jusqu'à {fin.strftime('%H:%M')} - ({heures}h{minutes:02d})")
        nom = st.text_input("📃 Nom de la tâche :", st.session_state.nom_tache_user)
        if st.button("📌 Ajouter au planning"):
            st.session_state.admin_planning.append((
                debut.date().isoformat(),
                debut.strftime("%H:%M"),
                fin.strftime("%H:%M"),
                nom
            ))
            st.write("✅ DEBUG : tâche ajoutée")

            st.session_state.commande_validee = False
            st.success("Ajouté.")
            st.rerun()

    if st.session_state.admin_planning:
        with st.expander("📊 Gantt", expanded=True):
            afficher_gantt(st.session_state.admin_planning)
