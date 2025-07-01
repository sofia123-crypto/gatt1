import streamlit as st
import pandas as pd
import numpy as np
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

    planning_df = pd.DataFrame(
        st.session_state.admin_planning,
        columns=["date", "heure_debut", "heure_fin", "nom"]
    )
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

    try:
        df_gantt = pd.DataFrame(planning, columns=["date", "heure_debut", "heure_fin", "nom"])
        df_gantt["Début"] = pd.to_datetime(df_gantt["date"] + " " + df_gantt["heure_debut"], errors='coerce')
        df_gantt["Fin"] = pd.to_datetime(df_gantt["date"] + " " + df_gantt["heure_fin"], errors='coerce')
        df_gantt.dropna(subset=["Début", "Fin"], inplace=True)

        if df_gantt.empty:
            st.warning("Aucune donnée valide pour le Gantt.")
            return

        df_gantt["Jour"] = pd.to_datetime(df_gantt["date"]).dt.strftime("%A %d/%m")
        df_gantt["Tâche"] = df_gantt["nom"]

        fig = px.timeline(df_gantt, x_start="Début", x_end="Fin", y="Jour", color="Tâche", title="📅 Planning Gantt par jour")
        fig.update_yaxes(autorange="reversed", title="Jour")
        fig.update_xaxes(tickformat="%H:%M", dtick=3600000)
        fig.update_layout(height=600, title_font_size=22)

        st.plotly_chart(fig, use_container_width=True)

        st.download_button(
            label="📥 Télécharger le planning CSV",
            data=df_gantt[["date", "heure_debut", "heure_fin", "nom"]].to_csv(index=False).encode("utf-8"),
            file_name="planning_gantt.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"❌ Erreur lors de l'affichage du Gantt : {e}")

def calculer_temps(commande_df, base_df):
    total = 0
    erreurs = []
    commande_df.columns = commande_df.columns.str.strip().str.lower().str.replace(' ', '').str.replace('\ufeff', '')
    base_df.columns = base_df.columns.str.strip().str.lower().str.replace(' ', '').str.replace('\ufeff', '')

    if 'reference' not in commande_df.columns or 'quantite' not in commande_df.columns:
        erreurs.append("Colonnes 'reference' ou 'quantite' manquantes dans la commande")
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
        erreurs.append(f"Conversion 'quantite' invalide : {e}")
        return 0, erreurs

    df_merge = commande_df.merge(base_df[['reference', 'temps_montage']], on='reference', how='left')
    df_merge['temps_total'] = df_merge['quantite'] * df_merge['temps_montage']
    total = df_merge['temps_total'].sum()
    missing_refs = df_merge[df_merge['temps_montage'].isna()]['reference'].unique()
    for ref in missing_refs:
        erreurs.append(f"Référence manquante dans la base : {ref}")

    return int(total), erreurs

# --- Initialisation ---
if 'admin_planning' not in st.session_state:
    st.session_state.admin_planning = []
if 'commande_df' not in st.session_state:
    st.session_state.commande_df = pd.DataFrame()

# --- Interface ---
role = st.sidebar.radio("👤 Choisissez votre rôle :", ["Utilisateur", "Administrateur"])

if role == "Administrateur":
    mdp = st.sidebar.text_input("🔐 Entrez le mot de passe :", type="password")
    if mdp != "safran123":
        st.warning("Mot de passe incorrect.")
        st.stop()

    st.success("✅ Accès administrateur accordé")
    st.header("📅 Configuration du Planning")

    date_plan = st.date_input("Date", value=datetime.today())
    h_debut, h_fin = st.columns(2)
    heure_debut = h_debut.time_input("Début de journée", time(8, 0))
    heure_fin = h_fin.time_input("Fin de journée", time(17, 0))

    with st.form("form_admin"):
        st.subheader("➕ Ajouter une tâche")
        col1, col2, col3 = st.columns([1, 1, 2])
        tache_debut = col1.time_input("Heure début", time(9, 0), key="admin_debut")
        tache_fin = col2.time_input("Heure fin", time(10, 0), key="admin_fin")
        tache_nom = col3.text_input("Nom de la tâche", "Réunion", key="admin_nom")

        if st.form_submit_button("Ajouter la tâche"):
            if tache_debut >= tache_fin:
                st.error("L'heure de fin doit être après l'heure de début.")
            elif not tache_nom:
                st.error("Veuillez saisir un nom de tâche.")
            else:
                st.session_state.admin_planning.append((str(date_plan), tache_debut.strftime("%H:%M"), tache_fin.strftime("%H:%M"), tache_nom))
                st.success("Tâche ajoutée avec succès.")
                st.rerun()

    if st.session_state.admin_planning:
        st.subheader("📋 Tâches planifiées")
        df_taches = pd.DataFrame(st.session_state.admin_planning, columns=["Date", "Heure début", "Heure fin", "Description"])
        st.dataframe(df_taches)

        with st.expander("📊 Diagramme de Gantt", expanded=True):
            afficher_gantt(st.session_state.admin_planning)

        if st.button("🧹 Réinitialiser le planning"):
            st.session_state.admin_planning = []
            st.success("Planning vidé.")
            st.rerun()

elif role == "Utilisateur":
    st.info("ℹ️ Calcul des temps de montage - Version 2.0")

    try:
        base_df = pd.read_csv("Test_1.csv")
        base_df.columns = base_df.columns.str.strip().str.lower().str.replace(' ', '')

        if 'temps_montage' not in base_df.columns:
            st.error("❌ La base doit contenir 'temps_montage'")
            st.stop()

        base_df['temps_montage'] = pd.to_numeric(base_df['temps_montage'], errors='coerce').fillna(0).astype(int)
        st.success("✅ Base chargée - Colonnes: " + ", ".join(base_df.columns))

    except Exception as e:
        st.error(f"❌ Erreur base: {str(e)}")
        st.stop()

    commande_file = st.file_uploader("📄 Déposer votre commande CSV", type="csv")
    if commande_file:
        try:
            commande_df = pd.read_csv(commande_file)
            commande_df.columns = commande_df.columns.str.strip().str.lower().str.replace(' ', '').str.replace('\ufeff', '')
            st.session_state.commande_df = commande_df
            st.success("✅ Commande importée avec succès.")
            st.dataframe(commande_df.head())
        except Exception as e:
            st.error(f"🚥 Erreur lecture fichier : {str(e)}")
            st.stop()

    if not st.session_state.commande_df.empty:
        if st.button("⏱ Calculer", type="primary"):
            with st.spinner(" Analyse en cours..."):
                commande_df = st.session_state.commande_df
                total, erreurs = calculer_temps(commande_df, base_df)

                if total > 0:
                    heures = total // 60
                    minutes = total % 60
                    st.success(f"⏳ Temps total estimé : **{heures}h{minutes:02d}min** ({total} minutes)")

                    debut_dispo, fin_dispo = trouver_prochaine_dispo(total)
                    if debut_dispo and fin_dispo:
                        date_str = debut_dispo.strftime("%A %d/%m/%Y à %H:%M")
                        st.success(f"📆 Disponible le **{date_str}** jusqu'à {fin_dispo.strftime('%H:%M')}")

                        nom_tache = st.text_input("📄 Nom de la tâche à ajouter :", "Montage client", key="user_nom")
                        ajout = st.button("📌 Ajouter au planning", key="user_ajout")

                        if ajout:
                            st.session_state.admin_planning.append((
                                debut_dispo.date().isoformat(),
                                debut_dispo.strftime("%H:%M"),
                                fin_dispo.strftime("%H:%M"),
                                nom_tache
                            ))
                            st.success("Tâche ajoutée au planning.")
                            st.rerun()

                if erreurs:
                    st.warning("⚠️ Alertes :")
                    for e in erreurs:
                        st.write(f"- {e}")

        if st.session_state.admin_planning:
            with st.expander("📊 Visualisation du planning Gantt", expanded=True):
                afficher_gantt(st.session_state.admin_planning)
    else:
        st.info("📅 Veuillez importer une commande.")

