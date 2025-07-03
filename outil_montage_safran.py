# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import plotly.express as px
import plotly.graph_objects as go

# Initialisation session
if "admin_planning" not in st.session_state:
    st.session_state.admin_planning = []

st.set_page_config(page_title="🛠️ Calcul du Temps de Montage", layout="wide")
st.title("🔧 Estimation du Temps de Montage")

# -----------------------------
# 🔧 Fonctions Utilitaires
# -----------------------------
def calculer_temps(commande_df, base_df):
    total_minutes = 0
    erreurs = []
    for _, ligne in commande_df.iterrows():
        ref = str(ligne["reference"]).strip()
        qte = ligne.get("quantite", 1)
        try:
            qte = int(qte)
        except:
            erreurs.append(f"❌ Quantité invalide pour {ref}")
            continue

        match = base_df[base_df["reference"].str.strip() == ref]
        if not match.empty:
            temps = int(match.iloc[0]["temps_montage"])
            total_minutes += temps * qte
        else:
            erreurs.append(f"❌ Référence inconnue : {ref}")
    return total_minutes, erreurs

def trouver_disponibilite(date_jour, h_debut_jour, h_fin_jour, planning, temps_requis):
    debut_jour = datetime.combine(date_jour, h_debut_jour)
    fin_jour = datetime.combine(date_jour, h_fin_jour)
    temps_requis_td = timedelta(minutes=temps_requis)
    taches = []

    for _, row in planning.iterrows():
        if pd.to_datetime(row["date"]).date() == date_jour:
            try:
                debut = datetime.combine(date_jour, datetime.strptime(row["heure_debut"], "%H:%M").time())
                fin = datetime.combine(date_jour, datetime.strptime(row["heure_fin"], "%H:%M").time())
                taches.append((debut, fin))
            except:
                continue

    taches.sort()
    cursor = debut_jour
    plages_libres = []
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

    df = pd.DataFrame(st.session_state.admin_planning, columns=["date", "heure_debut", "heure_fin", "nom"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    today = datetime.today().date()

    for i in range(30):
        jour = today + timedelta(days=i)
        debut, fin = trouver_disponibilite(jour, time(8, 0), time(17, 0), df, temps_total_minutes)
        if debut and fin:
            return debut, fin
    return None, None

def afficher_gantt(planning):
    if not planning:
        st.warning("Aucune donnée à afficher.")
        return

    try:
        df = pd.DataFrame(planning, columns=["date", "heure_debut", "heure_fin", "nom"])
        df["Début"] = pd.to_datetime(df["date"] + " " + df["heure_debut"], errors='coerce')
        df["Fin"] = pd.to_datetime(df["date"] + " " + df["heure_fin"], errors='coerce')
        df.dropna(subset=["Début", "Fin"], inplace=True)

        # Semaine à afficher
        semaine = [datetime.today().date() + timedelta(days=i) for i in range(7)]
        jours_str = [j.strftime("%d/%m") for j in semaine]

        # Préparer le graphe
        fig = go.Figure()
        palette = px.colors.qualitative.Plotly
        noms_uniques = sorted(df["nom"].unique())
        couleurs = {nom: palette[i % len(palette)] for i, nom in enumerate(noms_uniques)}

        # Ajouter les barres de tâches
        for _, row in df.iterrows():
            jour_obj = pd.to_datetime(row["date"]).date()
            if jour_obj not in semaine:
                continue

            jour_str = jour_obj.strftime("%d/%m")
            heure_debut = datetime.strptime(row["heure_debut"], "%H:%M")
            heure_fin = datetime.strptime(row["heure_fin"], "%H:%M")
            y0 = heure_debut.hour + heure_debut.minute / 60
            y1 = heure_fin.hour + heure_fin.minute / 60

            fig.add_trace(go.Bar(
                x=[jour_str],
                y=[y1 - y0],
                base=y0,
                width=0.6,
                marker_color=couleurs[row["nom"]],
                name=row["nom"],
                hovertemplate=(f"{row['nom']}<br>{row['heure_debut']} - {row['heure_fin']}<extra></extra>"),
                showlegend=True
            ))

        # Ajouter une barre transparente pour les jours sans tâche
        jours_existants = df["Début"].dt.strftime("%d/%m").unique()
        jours_vides = [j for j in jours_str if j not in jours_existants]

        for jour_str in jours_vides:
            fig.add_trace(go.Bar(
                x=[jour_str],
                y=[0.1],  # Petite barre invisible
                base=8,
                width=0.6,
                marker_color="rgba(0,0,0,0)",  # Transparent
                hoverinfo="skip",
                showlegend=False
            ))

        # Layout final
        fig.update_layout(
            title="📅 Planning Hebdomadaire",
            xaxis=dict(title="Date", side="top", categoryorder="array", categoryarray=jours_str),
            yaxis=dict(
                title="Heure",
                range=[8, 17],
                autorange="reversed",
                tickvals=list(range(8, 18)),
                ticktext=[f"{h:02d}:00" for h in range(8, 18)]
            ),
            height=600,
            showlegend=True
        )

        # Centrage visuel du diagramme
        with st.container():
            c1, c2, c3 = st.columns([1, 6, 1])
            with c2:
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Erreur Gantt : {e}")

# -----------------------------
# 🧑 Interface principale
# -----------------------------
role = st.sidebar.radio("👤 Choisissez votre rôle :", ["Utilisateur", "Administrateur"])

if role == "Administrateur":
    mdp = st.sidebar.text_input("🔐 Mot de passe :", type="password")
    if mdp != "safran123":
        st.warning("Mot de passe incorrect.")
        st.stop()

    st.success("✅ Accès admin accordé")
    st.header("📅 Configuration du planning")
    date_plan = st.date_input("Date", value=datetime.today())
    h_debut, h_fin = st.columns(2)
    heure_debut = h_debut.time_input("Début de journée", time(8, 0))
    heure_fin = h_fin.time_input("Fin de journée", time(17, 0))

    with st.form("form_admin"):
        st.subheader("➕ Ajouter une tâche")
        col1, col2, col3 = st.columns([1, 1, 2])
        t_debut = col1.time_input("Heure début", time(9, 0))
        t_fin = col2.time_input("Heure fin", time(10, 0))
        nom = col3.text_input("Nom", "Tâche")

        if st.form_submit_button("Ajouter"):
            if t_debut >= t_fin:
                st.error("L'heure de fin doit être après le début.")
            elif not nom:
                st.error("Nom requis.")
            else:
                st.session_state.admin_planning.append((
                    str(date_plan), t_debut.strftime("%H:%M"), t_fin.strftime("%H:%M"), nom
                ))
                st.success("✅ Tâche ajoutée.")

    if st.session_state.admin_planning:
        st.subheader("📋 Tâches planifiées")
        df = pd.DataFrame(st.session_state.admin_planning, columns=["Date", "Heure début", "Heure fin", "Nom"])
        st.dataframe(df)
        with st.expander("📊 Diagramme Gantt", expanded=True):
            afficher_gantt(st.session_state.admin_planning)
        if st.button("🧹 Réinitialiser le planning"):
            st.session_state.admin_planning = []
            st.success("Planning réinitialisé.")
            st.experimental_rerun()

elif role == "Utilisateur":
    st.info("ℹ️ Chargement des données de montage")

    # --- Chargement de la base ---
    try:
        base_df = pd.read_csv("Test_1.csv")
        base_df.columns = (
            base_df.columns
            .str.strip()
            .str.lower()
            .str.replace('\ufeff', '', regex=False)
            .str.replace(' ', '_')
        )

        st.write("🔎 Colonnes chargées :", base_df.columns.tolist())  # DEBUG

        if 'reference' not in base_df.columns or 'temps_montage' not in base_df.columns:
            st.error("❌ La base doit contenir les colonnes 'reference' et 'temps_montage'")
            st.stop()

        base_df['temps_montage'] = pd.to_numeric(base_df['temps_montage'], errors='coerce').fillna(0).astype(int)
        st.success("✅ Base chargée - Colonnes: " + ", ".join(base_df.columns))

    except Exception as e:
        st.error(f"❌ Erreur chargement base : {str(e)}")
        st.stop()

    # --- Chargement de la commande ---
    fichier_commande = st.file_uploader("📄 Charger votre commande", type="csv")
    if fichier_commande:
        try:
            commande_df = pd.read_csv(fichier_commande)
            commande_df.columns = commande_df.columns.str.strip().str.lower().str.replace(" ", "")
            commande_df["reference"] = commande_df["reference"].astype(str).str.strip()
            st.session_state.commande_df = commande_df
            st.success("✅ Commande importée")
            st.dataframe(commande_df)
        except Exception as e:
            st.error(f"❌ Erreur lecture commande : {e}")
            st.stop()

    # --- Calcul du temps de montage ---
    if "commande_df" in st.session_state and not st.session_state.commande_df.empty:
        if st.button("⏱ Calculer le temps"):
            total, erreurs = calculer_temps(st.session_state.commande_df, base_df)
            for err in erreurs:
                st.warning(err)
            if total > 0:
                heures = total // 60
                minutes = total % 60
                st.success(f"🕒 Temps total : {heures}h{minutes:02d} ({total} minutes)")

                debut_dispo, fin_dispo = trouver_prochaine_dispo(total)
                if debut_dispo and fin_dispo:
                    debut_dispo += timedelta(minutes=15)
                    fin_dispo += timedelta(minutes=15)
                    st.success(f"📆 Disponibilité : {debut_dispo.strftime('%A %d/%m/%Y %H:%M')} jusqu'à {fin_dispo.strftime('%H:%M')}")
                    st.session_state.debut_suggere = debut_dispo
                    st.session_state.fin_suggere = fin_dispo
                    st.session_state.duree_suggeree = total

    # --- Ajout de la tâche suggérée ---
    if "debut_suggere" in st.session_state:
        with st.form("ajout_tache_utilisateur"):
            st.subheader("📌 Ajouter au planning")
            nom = st.text_input("Nom de la tâche", "Montage client")
            date = st.date_input("Date", value=st.session_state.debut_suggere.date())
            col1, col2 = st.columns(2)
            h_debut = col1.time_input("Heure début", value=st.session_state.debut_suggere.time())
            h_fin = col2.time_input("Heure fin", value=st.session_state.fin_suggere.time())

            if st.form_submit_button("Ajouter"):
                if h_debut >= h_fin:
                    st.error("Heure de fin doit être après le début.")
                else:
                    st.session_state.admin_planning.append((
                        date.strftime("%Y-%m-%d"), h_debut.strftime("%H:%M"),
                        h_fin.strftime("%H:%M"), nom
                    ))
                    st.success("✅ Tâche ajoutée au planning")

    # --- Affichage du Gantt ---
    if st.session_state.admin_planning:
        with st.expander("📊 Visualiser le planning", expanded=True):
            afficher_gantt(st.session_state.admin_planning)

