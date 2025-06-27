
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

    taches = [
        (datetime.combine(date_jour, datetime.strptime(row["heure_debut"], "%H:%M").time()),
         datetime.combine(date_jour, datetime.strptime(row["heure_fin"], "%H:%M").time()))
        for _, row in planning.iterrows() if row["date"] == str(date_jour)
    ]
    taches.sort()

    plages_libres = []
    cursor = debut_jour
    for d, f in taches:
        if cursor < d:
            plages_libres.append((cursor, d))
        cursor = max(cursor, f)
    if cursor < fin_jour:
        plages_libres.append((cursor, fin_jour))

    for debut, fin in plages_libres:
        if fin - debut >= temps_requis_td:
            return debut, debut + temps_requis_td  # Retourne les heures exactes
    return None, None

def afficher_gantt(planning):
    df_gantt = pd.DataFrame(planning, columns=["date", "heure_debut", "heure_fin", "nom"])
    df_gantt["Début"] = pd.to_datetime(df_gantt["date"] + " " + df_gantt["heure_debut"])
    df_gantt["Fin"] = pd.to_datetime(df_gantt["date"] + " " + df_gantt["heure_fin"])
    df_gantt["Jour"] = pd.to_datetime(df_gantt["date"]).dt.strftime("%A %d/%m")
    df_gantt["Tâche"] = df_gantt["nom"]

    fig = px.timeline(
        df_gantt, x_start="Début", x_end="Fin", y="Jour", color="Tâche", title="📅 Planning Gantt par jour"
    )
    fig.update_yaxes(autorange="reversed", title="Jour")
    fig.update_xaxes(
        tickformat="%H:%M",
        dtick=3600000,
        range=[df_gantt["Début"].min() - pd.Timedelta(hours=1),
               df_gantt["Fin"].max() + pd.Timedelta(hours=1)],
        title="Heure de la journée"
    )
    fig.update_layout(
        height=800,
        title_font_size=22,
        font=dict(size=14),
        margin=dict(l=80, r=80, t=80, b=80),
        title_x=0.5,
        plot_bgcolor="white",
        paper_bgcolor="white"
    )

    st.markdown("### 📊 Visualisation Gantt")
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.plotly_chart(fig, use_container_width=False)

def calculer_temps(commande_df, base_df):
    total = 0
    erreurs = []
    for _, ligne in commande_df.iterrows():
        ref = ligne['reference']
        qte = ligne['quantite']
        ligne_base = base_df[base_df['reference'] == ref]
        if not ligne_base.empty:
            try:
                temps = int(ligne_base.iloc[0]['temps_montage'])
                total += temps * qte
            except:
                erreurs.append(f"Erreur de conversion pour : {ref}")
        else:
            erreurs.append(f"Référence inconnue : {ref}")
    return total, erreurs

# --- Interface principale ---

role = st.sidebar.radio("👤 Choisissez votre rôle :", ["Utilisateur", "Administrateur"])

if role == "Administrateur":
    mdp = st.text_input("🔐 Entrez le mot de passe :", type="password")
    if mdp != "safran123":
        st.warning("Mot de passe incorrect.")
        st.stop()

    st.success("✅ Accès administrateur accordé")

    date_plan = st.date_input("📅 Date", value=datetime.today())
    h_debut, h_fin = st.columns(2)
    heure_debut = h_debut.time_input("Début de journée", time(8, 0))
    heure_fin = h_fin.time_input("Fin de journée", time(17, 0))

    if "admin_planning" not in st.session_state:
        st.session_state.admin_planning = []

    with st.form("form_admin"):
        col1, col2, col3 = st.columns([1, 1, 2])
        tache_debut = col1.time_input("Heure début", time(9, 0))
        tache_fin = col2.time_input("Heure fin", time(10, 0))
        tache_nom = col3.text_input("Nom de la tâche")

        if st.form_submit_button("➕ Ajouter"):
            if tache_debut < tache_fin and tache_nom:
                st.session_state.admin_planning.append(
                    (str(date_plan), tache_debut.strftime("%H:%M"), tache_fin.strftime("%H:%M"), tache_nom)
                )
                st.success("Tâche ajoutée.")
            else:
                st.error("⚠️ Vérifiez les heures et le nom de la tâche.")

    if st.session_state.admin_planning:
        st.markdown("### 📋 Tâches ajoutées :")
        for i, (jour, d, f, nom) in enumerate(st.session_state.admin_planning):
            st.text(f"{i+1}. {jour} | {d} → {f} | {nom}")

        col_reset, col_save = st.columns(2)
        if col_reset.button("🗑️ Réinitialiser"):
            st.session_state.admin_planning.clear()
        if col_save.button("💾 Sauvegarder"):
            pd.DataFrame(st.session_state.admin_planning,
                         columns=["date", "heure_debut", "heure_fin", "nom"]).to_csv("planning_admin.csv", index=False)
            st.success("Planning sauvegardé.")

        with st.expander("📊 Cliquer pour voir le Planning Gantt", expanded=False):
            afficher_gantt(st.session_state.admin_planning)

elif role == "Utilisateur":
    st.info("Les temps de montage sont basés sur des estimations fictives.")

    try:
        base_df = pd.read_csv("Test_1.csv")
        base_df['temps_montage'] = base_df['temps_montage'].astype(int)
    except Exception as e:
        st.error(f"❌ Erreur chargement `Test_1.csv` : {e}")
        st.stop()

    commande_file = st.file_uploader("📤 Charger votre commande", type="csv")
    if commande_file:
        erreurs = []

        try:
            commande_df = pd.read_csv(commande_file, sep=None, engine="python", encoding="utf-8")
            commande_df.columns = commande_df.columns.str.strip().str.lower()

            commande_df['quantite'] = pd.to_numeric(commande_df['quantite'], errors='coerce').fillna(0).astype(int)

            try:
                df_plan = pd.read_csv("planning_admin.csv")
            except:
                st.warning("⚠️ Aucun planning trouvé.")
                df_plan = pd.DataFrame(columns=["date", "heure_debut", "heure_fin", "nom"])

            if st.button("▶️ Calculer le temps de montage"):
                total, erreurs = calculer_temps(commande_df, base_df)

                if df_plan.empty:
                    st.error("❌ Aucun planning disponible.")
                    st.stop()

                dates_planning = sorted(df_plan["date"].unique())
                dispo = None
                for d in dates_planning:
                    d_obj = pd.to_datetime(d).date()
                    debut, fin = trouver_disponibilite(d_obj, time(8, 0), time(17, 0), df_plan, total)
                    if debut and fin:
                        dispo = (d, debut, fin)
                        break

                st.success(f"🕒 Temps total estimé : {total} minutes")

                if dispo:
                    d, h_debut, h_fin = dispo
                    st.info(f"📆 Disponibilité estimée le **{d}** de **{h_debut.strftime('%H:%M')} à {h_fin.strftime('%H:%M')}**")

                    new_row = pd.DataFrame([{
                        "date": d,
                        "heure_debut": h_debut.strftime("%H:%M"),
                        "heure_fin": h_fin.strftime("%H:%M"),
                        "nom": "Montage Poste Client"
                    }])
                    df_plan = pd.concat([df_plan, new_row], ignore_index=True)
                    df_plan.to_csv("planning_admin.csv", index=False)
                    st.success("✅ Le planning a été mis à jour avec la nouvelle tâche.")
                else:
                    st.warning("❌ Aucune plage horaire suffisante trouvée dans les jours planifiés.")

                if erreurs:
                    st.warning("⚠️ Problèmes détectés :")
                    for e in erreurs:
                        st.text(f" - {e}")

                with st.expander("📊 Voir le planning Gantt", expanded=False):
                    afficher_gantt(df_plan.values.tolist())

        except Exception as e:
            st.error(f"❌ Erreur traitement fichier : {e}")
