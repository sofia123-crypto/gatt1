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

    # Vérification des colonnes requises
    colonnes_requises = {'reference', 'quantite'}
    if not colonnes_requises.issubset(commande_df.columns):
        erreurs.append(f"❌ Colonnes requises manquantes : {colonnes_requises - set(commande_df.columns)}")
        return 0, erreurs

    # Vérification des données de base
    if base_df.empty:
        erreurs.append("❌ La base de données des temps de montage est vide.")
        return 0, erreurs

    for _, ligne in commande_df.iterrows():
        try:
            ref = str(ligne['reference']).strip()
            qte = int(ligne['quantite'])
        except (ValueError, KeyError) as e:
            erreurs.append(f"Erreur d'accès aux données ligne {_ + 2}: {e}")
            continue

        # Recherche dans la base de données
        ligne_base = base_df[base_df['reference'].astype(str).str.strip() == ref]
        
        if ligne_base.empty:
            erreurs.append(f"Référence inconnue : {ref}")
            continue
            
        try:
            temps = int(ligne_base.iloc[0]['temps_montage'])
            total += temps * qte
        except (ValueError, KeyError) as e:
            erreurs.append(f"Erreur conversion temps pour {ref} : {e}")

    return total, erreurs

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
    st.info("ℹ️ Les temps de montage sont basés sur des estimations standards.")
    
    # Chargement de la base de données des temps
    try:
        base_df = pd.read_csv("Test_1.csv")
        base_df['temps_montage'] = pd.to_numeric(base_df['temps_montage'], errors='coerce').fillna(0).astype(int)
        if base_df.empty:
            st.error("La base de données des temps est vide.")
            st.stop()
    except FileNotFoundError:
        st.error("Fichier 'Test_1.csv' introuvable.")
        st.stop()
    except Exception as e:
        st.error(f"Erreur lors du chargement de 'Test_1.csv': {e}")
        st.stop()

    # Upload du fichier de commande
    st.header("📤 Importation de la commande")
    commande_file = st.file_uploader("Choisir un fichier CSV", type="csv")
    
    if commande_file is not None:
        try:
            # Lecture du fichier de commande
            commande_df = pd.read_csv(commande_file, sep=None, engine='python')
            commande_df.columns = commande_df.columns.str.strip().str.lower()
            
            # Vérification des colonnes requises
            if not {'reference', 'quantite'}.issubset(commande_df.columns):
                st.error("Le fichier doit contenir les colonnes 'reference' et 'quantite'.")
                st.stop()
                
            # Conversion des quantités
            commande_df['quantite'] = pd.to_numeric(commande_df['quantite'], errors='coerce').fillna(0).astype(int)
            
            # Affichage des données
            st.success("Fichier chargé avec succès.")
            st.dataframe(commande_df.head())

            # Chargement du planning existant
            try:
                df_plan = pd.read_csv("planning_admin.csv")
            except FileNotFoundError:
                st.warning("Aucun planning trouvé. Veuillez contacter l'administrateur.")
                df_plan = pd.DataFrame(columns=["date", "heure_debut", "heure_fin", "nom"])
            except Exception as e:
                st.error(f"Erreur lors du chargement du planning : {e}")
                df_plan = pd.DataFrame(columns=["date", "heure_debut", "heure_fin", "nom"])

            # Bouton de calcul
            if st.button("⏱️ Calculer le temps de montage"):
                with st.spinner("Calcul en cours..."):
                    total, erreurs = calculer_temps(commande_df, base_df)
                    
                    st.success(f"🕒 Temps total estimé : {total} minutes (≈ {total//60}h{total%60}min)")
                    
                    if erreurs:
                        st.warning("⚠️ Problèmes détectés :")
                        for e in erreurs:
                            st.text(f" - {e}")
                    
                    # Recherche de disponibilité
                    if not df_plan.empty:
                        dates_planning = pd.to_datetime(df_plan["date"].unique()).date
                        dispo = None
                        
                        for d in sorted(dates_planning):
                            debut, fin = trouver_disponibilite(
                                d, time(8, 0), time(17, 0), df_plan, total
                            )
                            if debut and fin:
                                dispo = (d.strftime("%Y-%m-%d"), debut, fin)
                                break
                                
                        if dispo:
                            d, h_debut, h_fin = dispo
                            st.info(
                                f"📆 Disponibilité estimée le **{d}** "
                                f"de **{h_debut.strftime('%H:%M')} à {h_fin.strftime('%H:%M')}**"
                            )
                            
                            # Mise à jour du planning
                            new_row = pd.DataFrame([{
                                "date": d,
                                "heure_debut": h_debut.strftime("%H:%M"),
                                "heure_fin": h_fin.strftime("%H:%M"),
                                "nom": "Montage Poste Client"
                            }])
                            
                            try:
                                df_plan = pd.concat([df_plan, new_row], ignore_index=True)
                                df_plan.to_csv("planning_admin.csv", index=False)
                                st.success("✅ Planning mis à jour avec la nouvelle tâche.")
                            except Exception as e:
                                st.error(f"Erreur lors de la mise à jour du planning : {e}")
                        else:
                            st.warning("Aucune plage horaire suffisante trouvée dans les jours planifiés.")
                            
                        # Affichage du Gantt
                        with st.expander("📊 Voir le planning complet", expanded=True):
                            afficher_gantt(df_plan.values.tolist())
                    else:
                        st.warning("Aucun planning disponible pour la recherche de créneaux.")

        except Exception as e:
            st.error(f"Erreur lors du traitement du fichier : {str(e)}")
