import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import plotly.express as px
import plotly.graph_objects as go

# Initialize admin_planning list in session state if not present
if "admin_planning" not in st.session_state:
    st.session_state.admin_planning = []

st.set_page_config(page_title="🛠️ Calcul du Temps de Montage", layout="wide")
st.title("🔧 Estimation du Temps de Montage")

# --- Utility Functions ---
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
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime, timedelta

    if not planning:
        st.warning("Aucune donnée à afficher.")
        return

    try:
        df = pd.DataFrame(planning, columns=["date", "heure_debut", "heure_fin", "nom"])
        df["Début"] = pd.to_datetime(df["date"] + " " + df["heure_debut"], errors='coerce')
        df["Fin"] = pd.to_datetime(df["date"] + " " + df["heure_fin"], errors='coerce')
        df.dropna(subset=["Début", "Fin"], inplace=True)

        # 🗓 Générer les 7 jours à partir d’aujourd’hui
        today = datetime.today().date()
        semaine = [today + timedelta(days=i) for i in range(7)]
        jours_str = [jour.strftime("%d/%m") for jour in semaine]

        palette = px.colors.qualitative.Plotly
        couleurs = {nom: palette[i % len(palette)] for i, nom in enumerate(df["nom"].unique())}

        fig = go.Figure()

        for _, row in df.iterrows():
            jour_obj = pd.to_datetime(row["date"]).date()
            if jour_obj not in semaine:
                continue  # Ignorer les jours hors de la semaine affichée

            jour_str = jour_obj.strftime("%d/%m")
            heure_debut = datetime.strptime(row["heure_debut"], "%H:%M")
            heure_fin = datetime.strptime(row["heure_fin"], "%H:%M")
            h_debut_float = heure_debut.hour + heure_debut.minute / 60
            h_fin_float = heure_fin.hour + heure_fin.minute / 60

            fig.add_trace(go.Bar(
                x=[jour_str],
                y=[h_fin_float - h_debut_float],
                base=h_debut_float,
                width=0.6,
                marker_color=couleurs[row["nom"]],
                name=row["nom"],
                hovertemplate=(
                    f"{row['nom']}<br>"
                    f"{row['date']}<br>"
                    f"{row['heure_debut']} - {row['heure_fin']}<extra></extra>"
                )
            ))

        fig.update_layout(
            title="📅 Planning Hebdomadaire",
            xaxis=dict(
                title="Jour",
                categoryorder="array",
                categoryarray=jours_str,
                tickvals=jours_str,
                ticktext=jours_str,
                side="top"  # ✅ Les dates en haut
            ),
            yaxis=dict(
                title="Heure",
                tickmode="array",
                tickvals=list(range(8, 18)),
                ticktext=[f"{h:02d}:00" for h in range(8, 18)],
                autorange="reversed",  # ✅ 08:00 en haut
                range=[8, 17]
            ),
            height=600,
            margin=dict(l=60, r=30, t=60, b=60),
            showlegend=True,
            barmode="stack"
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Erreur affichage Gantt : {e}")




# --- Main Interface ---
role = st.sidebar.radio("👤 Choisissez votre rôle :", ["Utilisateur", "Administrateur"])

if role == "Administrateur":
    mdp = st.sidebar.text_input("🔐 Entrez le mot de passe :", type="password")
    if mdp != "safran123":
        st.warning("Mot de passe incorrect.")
        st.stop()

    st.success("✅ Accès administrateur accordé")
    st.header("📅 Configuration du Planning")

    # Make sure date_plan is defined here at top level for admin
    date_plan = st.date_input("Date", value=datetime.today())

    h_debut, h_fin = st.columns(2)
    heure_debut = h_debut.time_input("Début de journée", time(8, 0))
    heure_fin = h_fin.time_input("Fin de journée", time(17, 0))

    with st.form("form_admin"):
        st.subheader("➕ Ajouter une tâche")
        col1, col2, col3 = st.columns([1,1,2])
        tache_debut = col1.time_input("Heure début", time(9, 0), key="admin_debut")
        tache_fin = col2.time_input("Heure fin", time(10, 0), key="admin_fin")
        tache_nom = col3.text_input("Nom de la tâche", "Réunion", key="admin_nom")

        if st.form_submit_button("Ajouter la tâche"):
            if tache_debut >= tache_fin:
                st.error("L'heure de fin doit être après l'heure de début.")
            elif not tache_nom:
                st.error("Veuillez saisir un nom de tâche.")
            else:
                st.session_state.admin_planning.append((
                    str(date_plan),
                    tache_debut.strftime("%H:%M"),
                    tache_fin.strftime("%H:%M"),
                    tache_nom
                ))
                st.success("Tâche ajoutée avec succès.")

    if st.session_state.admin_planning:
        st.subheader("📋 Tâches planifiées")
        df_taches = pd.DataFrame(st.session_state.admin_planning, columns=["Date", "Heure début", "Heure fin", "Description"])
        st.dataframe(df_taches)

        with st.expander("📊 Diagramme de Gantt", expanded=True):
            afficher_gantt(st.session_state.admin_planning)

        if st.button("🧹 Réinitialiser le planning"):
            st.session_state.admin_planning = []
            st.success("Planning vidé.")
            st.experimental_rerun()

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

    if "commande_df" in st.session_state and not st.session_state.commande_df.empty:
        if st.button("⏱ Calculer"):
            with st.spinner(" Analyse en cours..."):
                commande_df = st.session_state.commande_df
                total, erreurs = calculer_temps(commande_df, base_df)

                if total > 0:
                    heures = total // 60
                    minutes = total % 60
                    st.success(f"⏳ Temps total estimé : **{heures}h{minutes:02d}min** ({total} minutes)")

                    debut_dispo, fin_dispo = trouver_prochaine_dispo(total)
                    # ➕ Ajouter une marge de 15 minutes entre les tâches
                    debut_dispo += timedelta(minutes=15)
                    fin_dispo += timedelta(minutes=15)

                    if debut_dispo and fin_dispo:
                        date_str = debut_dispo.strftime("%A %d/%m/%Y à %H:%M")
                        st.success(f"📆 Disponible le **{date_str}** jusqu'à {fin_dispo.strftime('%H:%M')}")

                    # On sauvegarde cette dispo dans session_state
                        st.session_state.debut_suggere = debut_dispo
                        st.session_state.fin_suggere = fin_dispo
                        st.session_state.duree_suggeree = total

# On affiche toujours le formulaire si une dispo a été calculée
    if "debut_suggere" in st.session_state and "fin_suggere" in st.session_state:
        with st.form("ajout_tache_form"):
            st.subheader("📌 Ajouter cette tâche au planning")
            nom_tache = st.text_input("📄 Nom de la tâche :", "Montage client")
            date_tache = st.date_input("📅 Date", value=st.session_state.debut_suggere.date())
            col1, col2 = st.columns(2)
            heure_debut = col1.time_input("Heure début", value=st.session_state.debut_suggere.time())
            heure_fin = col2.time_input("Heure fin", value=st.session_state.fin_suggere.time())

            ajouter = st.form_submit_button("✅ Ajouter au planning")
            if ajouter:
                if heure_debut >= heure_fin:
                    st.error("L'heure de fin doit être après le début.")
                elif not nom_tache.strip():
                    st.error("Veuillez saisir un nom.")
                else:
                    st.session_state.admin_planning.append((
                        date_tache.strftime("%Y-%m-%d"),
                        heure_debut.strftime("%H:%M"),
                        heure_fin.strftime("%H:%M"),
                        nom_tache.strip()
                    ))
                    st.success("✅ Tâche ajoutée avec succès.")

    st.write("📦 DEBUG - Tâches en mémoire :", st.session_state.admin_planning)

    if st.session_state.admin_planning:
        st.write("📦 Planning brut :", st.session_state.admin_planning)

        with st.expander("📊 Visualisation du planning Gantt", expanded=True):
            afficher_gantt(st.session_state.admin_planning)
    else:
        st.info("📅 Veuillez importer une commande.")
