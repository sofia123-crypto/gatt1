import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import plotly.express as px

# Configuration de la page
st.set_page_config(page_title="🛠️ Calcul du Temps de Montage", layout="wide")
st.title("🔧 Estimation du Temps de Montage")

# --- Fonctions Utilitaires ---

def trouver_disponibilite(date_jour, h_debut_jour, h_fin_jour, planning, temps_requis):
    """Trouve une plage horaire disponible dans le planning pour une durée donnée."""
    debut_jour = datetime.combine(date_jour, h_debut_jour)
    fin_jour = datetime.combine(date_jour, h_fin_jour)
    temps_requis_td = timedelta(minutes=temps_requis)

    # Récupère les tâches pour la date spécifiée
    taches = []
    for _, row in planning.iterrows():
        if row["date"] == str(date_jour):
            try:
                debut_tache = datetime.combine(date_jour, datetime.strptime(row["heure_debut"], "%H:%M").time())
                fin_tache = datetime.combine(date_jour, datetime.strptime(row["heure_fin"], "%H:%M").time())
                taches.append((debut_tache, fin_tache))
            except ValueError as e:
                st.warning(f"Format d'heure invalide dans le planning : {e}")
                continue
    
    taches.sort()

    # Trouve les plages libres entre les tâches
    plages_libres = []
    cursor = debut_jour
    
    for debut_tache, fin_tache in taches:
        if cursor < debut_tache:
            plages_libres.append((cursor, debut_tache))
        cursor = max(cursor, fin_tache)
    
    if cursor < fin_jour:
        plages_libres.append((cursor, fin_jour))

    # Vérifie les plages libres pour trouver une disponibilité
    for debut, fin in plages_libres:
        if fin - debut >= temps_requis_td:
            return debut, debut + temps_requis_td
    
    return None, None

def afficher_gantt(planning):
    """Affiche un diagramme de Gantt à partir du planning."""
    if not planning:
        st.warning("Aucune donnée à afficher dans le Gantt.")
        return
    
    try:
        df_gantt = pd.DataFrame(planning, columns=["date", "heure_debut", "heure_fin", "nom"])
        
        # Conversion des dates et heures
        df_gantt["Début"] = pd.to_datetime(df_gantt["date"] + " " + df_gantt["heure_debut"], errors='coerce')
        df_gantt["Fin"] = pd.to_datetime(df_gantt["date"] + " " + df_gantt["heure_fin"], errors='coerce')
        
        # Suppression des lignes avec des dates invalides
        df_gantt = df_gantt.dropna(subset=["Début", "Fin"])
        
        if df_gantt.empty:
            st.warning("Aucune donnée valide pour le Gantt.")
            return
            
        df_gantt["Jour"] = pd.to_datetime(df_gantt["date"]).dt.strftime("%A %d/%m")
        df_gantt["Tâche"] = df_gantt["nom"]

        # Création du graphique Gantt
        fig = px.timeline(
            df_gantt, 
            x_start="Début", 
            x_end="Fin", 
            y="Jour", 
            color="Tâche", 
            title="📅 Planning Gantt par jour"
        )
        
        # Configuration des axes
        fig.update_yaxes(autorange="reversed", title="Jour")
        fig.update_xaxes(
            tickformat="%H:%M",
            dtick=3600000,  # 1 heure en millisecondes
            range=[df_gantt["Début"].min() - pd.Timedelta(hours=1),
                   df_gantt["Fin"].max() + pd.Timedelta(hours=1)],
            title="Heure de la journée"
        )
        
        # Configuration du layout
        fig.update_layout(
            height=600,
            title_font_size=22,
            font=dict(size=14),
            margin=dict(l=80, r=80, t=80, b=80),
            title_x=0.5,
            plot_bgcolor="white",
            paper_bgcolor="white"
        )

        st.markdown("### 📊 Visualisation Gantt")
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Erreur lors de la génération du Gantt : {e}")

def calculer_temps(commande_df, base_df):
    """Calcule le temps total de montage pour une commande."""
    total = 0
    erreurs = []

    st.markdown("### 🧪 Diagnostic de `calculer_temps`")

    # 🔧 Nettoyage des noms de colonnes
    commande_df.columns = commande_df.columns.str.strip().str.lower().str.replace(' ', '').str.replace('\ufeff', '')
    base_df.columns = base_df.columns.str.strip().str.lower().str.replace(' ', '').str.replace('\ufeff', '')

    st.write("📋 Colonnes commande :", commande_df.columns.tolist())
    st.write("📋 Colonnes base :", base_df.columns.tolist())

    # ❌ Vérification des colonnes obligatoires
    if 'reference' not in commande_df.columns:
        erreurs.append("ERREUR: Colonne 'reference' manquante dans la commande")
        return 0, erreurs

    if 'quantite' not in commande_df.columns:
        erreurs.append("ERREUR: Colonne 'quantite' manquante dans la commande")
        return 0, erreurs

    if 'reference' not in base_df.columns:
        erreurs.append("ERREUR: Colonne 'reference' manquante dans la base")
        return 0, erreurs

    if 'temps_montage' not in base_df.columns:
        erreurs.append("ERREUR: Colonne 'temps_montage' manquante dans la base")
        return 0, erreurs

    # 🧹 Nettoyage des valeurs
    commande_df = commande_df.copy()
    base_df = base_df.copy()

    commande_df['reference'] = commande_df['reference'].astype(str).str.strip().str.upper()
    base_df['reference'] = base_df['reference'].astype(str).str.strip().str.upper()

    # Suppression des lignes sans référence
    commande_df = commande_df.dropna(subset=['reference'])
    commande_df = commande_df[commande_df['reference'].str.strip() != '']

    # Conversion des quantités
    try:
        commande_df['quantite'] = pd.to_numeric(commande_df['quantite'], errors='coerce').fillna(0).astype(int)
    except Exception as e:
        erreurs.append(f"ERREUR conversion 'quantite': {e}")
        return 0, erreurs

    # 🔗 Jointure avec la base
    df_merge = commande_df.merge(
        base_df[['reference', 'temps_montage']],
        on='reference',
        how='left'
    )

    st.write("🧾 Aperçu de la jointure :", df_merge.head())

    # Calcul du temps total
    df_merge['temps_total'] = df_merge['quantite'] * df_merge['temps_montage']
    total = df_merge['temps_total'].sum()

    # 🔔 Références non trouvées
    missing_refs = df_merge[df_merge['temps_montage'].isna()]['reference'].unique()
    for ref in missing_refs:
        erreurs.append(f"ATTENTION: Référence '{ref}' non trouvée dans la base")

    return int(total), erreurs

# --- Interface principale ---

# Initialisation des variables de session
if 'admin_planning' not in st.session_state:
    st.session_state.admin_planning = []

role = st.sidebar.radio("👤 Choisissez votre rôle :", ["Utilisateur", "Administrateur"])

if role == "Administrateur":
    mdp = st.sidebar.text_input("🔐 Entrez le mot de passe :", type="password")
    if mdp != "safran123":
        st.warning("Mot de passe incorrect.")
        st.stop()

    st.success("✅ Accès administrateur accordé")

    # Section configuration planning
    st.header("📅 Configuration du Planning")
    
    date_plan = st.date_input("Date", value=datetime.today())
    h_debut, h_fin = st.columns(2)
    heure_debut = h_debut.time_input("Début de journée", time(8, 0))
    heure_fin = h_fin.time_input("Fin de journée", time(17, 0))

    # Formulaire d'ajout de tâche
    with st.form("form_admin"):
        st.subheader("➕ Ajouter une tâche")
        col1, col2, col3 = st.columns([1, 1, 2])
        tache_debut = col1.time_input("Heure début", time(9, 0))
        tache_fin = col2.time_input("Heure fin", time(10, 0))
        tache_nom = col3.text_input("Nom de la tâche", "Réunion")

        if st.form_submit_button("Ajouter la tâche"):
            if tache_debut >= tache_fin:
                st.error("L'heure de fin doit être après l'heure de début.")
            elif not tache_nom:
                st.error("Veuillez saisir un nom de tâche.")
            else:
                st.session_state.admin_planning.append(
                    (str(date_plan), tache_debut.strftime("%H:%M"), tache_fin.strftime("%H:%M"), tache_nom)
                )
                st.success("Tâche ajoutée avec succès.")

    # Affichage des tâches existantes
    if st.session_state.admin_planning:
        st.subheader("📋 Tâches planifiées")
        df_taches = pd.DataFrame(
            st.session_state.admin_planning,
            columns=["Date", "Heure début", "Heure fin", "Description"]
        )
        st.dataframe(df_taches)

        # Boutons de gestion
        col_reset, col_save, col_export = st.columns(3)
        if col_reset.button("🗑️ Réinitialiser le planning"):
            st.session_state.admin_planning.clear()
            st.success("Planning réinitialisé.")
            
        if col_save.button("💾 Sauvegarder dans planning_admin.csv"):
            try:
                pd.DataFrame(
                    st.session_state.admin_planning,
                    columns=["date", "heure_debut", "heure_fin", "nom"]
                ).to_csv("planning_admin.csv", index=False)
                st.success("Planning sauvegardé avec succès.")
            except Exception as e:
                st.error(f"Erreur lors de la sauvegarde : {e}")
                
        if col_export.button("📤 Exporter vers Excel"):
            try:
                df = pd.DataFrame(
                    st.session_state.admin_planning,
                    columns=["date", "heure_debut", "heure_fin", "nom"]
                )
                df.to_excel("planning_admin.xlsx", index=False)
                st.success("Fichier Excel exporté avec succès.")
            except Exception as e:
                st.error(f"Erreur lors de l'export Excel : {e}")

        # Visualisation Gantt
        with st.expander("📊 Diagramme de Gantt", expanded=True):
            afficher_gantt(st.session_state.admin_planning)

elif role == "Utilisateur":
    st.info("ℹ️ Calcul des temps de montage - Version 2.0")
    
    # Chargement de la base
    try:
        base_df = pd.read_csv("Test_1.csv")
        st.success("✅ Base chargée - Colonnes: " + ", ".join(base_df.columns))
        
        # Nettoyage automatique
        base_df.columns = base_df.columns.str.strip().str.lower().str.replace(' ', '')
        
        if 'temps_montage' not in base_df.columns:
            st.error("❌ La base doit contenir 'temps_montage'")
            st.stop()
            
        base_df['temps_montage'] = pd.to_numeric(base_df['temps_montage'], errors='coerce').fillna(0).astype(int)
        
    except Exception as e:
        st.error(f"❌ Erreur base: {str(e)}")
        st.stop()

    # Upload commande
    commande_file = st.file_uploader("📤 Déposer votre commande CSV", type="csv")
    

if commande_file:
    try:
        # Lecture du CSV
        commande_df = pd.read_csv(commande_file)
        
        # Nettoyage des noms de colonnes (robuste)
        commande_df.columns = commande_df.columns.str.strip().str.lower().str.replace(' ', '').str.replace('\ufeff', '')
        
        # Sauvegarde dans la session
        st.session_state["commande_df"] = commande_df

        st.success("✅ Commande importée avec succès.")
        st.write("📄 Aperçu de la commande :")
        st.dataframe(commande_df.head())

    except Exception as e:
        st.error(f"💥 Erreur lors de la lecture du fichier : {str(e)}")
        st.write("Contenu du fichier (extrait) :")
        st.code(commande_file.getvalue().decode('utf-8')[:300])
        st.stop()

# 🧮 Bouton de calcul (visible uniquement si commande présente)
if "commande_df" in st.session_state and not st.session_state["commande_df"].empty:
    if st.button("⏱ Calculer", type="primary"):
        with st.spinner("🧠 Analyse en cours..."):
            commande_df = st.session_state["commande_df"]  # Chargement sécurisé
            total, erreurs = calculer_temps(commande_df, base_df)

            # ✅ Affichage du résultat
            if total > 0:
                heures = total // 60
                minutes = total % 60
                st.success(f"⏳ Temps total estimé : **{heures}h{minutes:02d}min** ({total} minutes)")

            # ⚠️ Affichage des erreurs ou alertes
            if erreurs:
                st.warning("⚠️ Alertes détectées :")
                for e in erreurs:
                    st.write(f"- {e}")
else:
    st.info("📝 Veuillez importer une commande pour activer le bouton de calcul.")
