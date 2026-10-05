"""Recettes d'artisanat de KINGDOM, par métier."""
import streamlit as st

import donnees as d

st.set_page_config(page_title="KINGDOM — Recettes", layout="wide")

st.title("KINGDOM — Recettes d'artisanat")

recettes = d.recettes()
ingredients = d.ingredients_recettes()
metiers = d.metiers_artisanat()
objets_par_id = d.objets().set_index("id")
equipements = d.pvp_equipements()
probabilites_rarete = d.probabilites_rarete()

onglet_metiers, onglet_profils, onglet_recolte = st.tabs(["Métiers", "Profils", "Ingrédients de récolte"])

with onglet_metiers:
    tri = st.radio(
        "Trier les recettes par",
        ["Niveau requis", "Efficacité XP (XP par effort de récolte)"],
        horizontal=True,
    )

    sous_onglets = st.tabs([m["name"] for _, m in metiers.iterrows()])

    for sous_onglet, (_, metier) in zip(sous_onglets, metiers.iterrows()):
        with sous_onglet:
            recettes_metier = recettes[recettes["station"] == metier["station"]].copy()
            recettes_metier["effort"] = recettes_metier["id"].apply(
                lambda recipe_id: d.effort_recette(recipe_id, ingredients, probabilites_rarete)
            )
            recettes_metier["efficacite"] = recettes_metier.apply(
                lambda r: d.efficacite_xp(r["xp"], r["effort"]), axis=1
            )
            if tri == "Niveau requis":
                recettes_metier = recettes_metier.sort_values("requiredJobLevel")
            else:
                recettes_metier = recettes_metier.sort_values("efficacite", ascending=False)

            for _, recette in recettes_metier.iterrows():
                titre = f"Niveau {recette['requiredJobLevel']} — {recette['resultName']} (+{int(recette['xp'])} XP)"
                if tri != "Niveau requis":
                    titre += f" — {recette['efficacite']:.1f} XP/effort"
                effet = d.effet_objet(recette["resultItemId"], objets_par_id, equipements) or d.usage_materiau(
                    recette["resultItemId"], ingredients
                )
                cle_ouverte = f"ouvert_{recette['id']}"
                st.session_state.setdefault(cle_ouverte, False)

                with st.container(border=True):
                    st.markdown(
                        "<div style='display:flex; justify-content:space-between; "
                        "align-items:center; gap:1rem;'>"
                        f"<span>{titre}</span>"
                        f"<span style='white-space:nowrap;'>{effet or ''}</span>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    ouvert = st.session_state[cle_ouverte]
                    if st.button("Masquer les ingrédients" if ouvert else "Voir les ingrédients", key=f"bouton_{recette['id']}"):
                        st.session_state[cle_ouverte] = not ouvert

                    if st.session_state[cle_ouverte]:
                        ses_ingredients = ingredients[ingredients["recipeId"] == recette["id"]].copy()
                        ses_ingredients["Provenance"] = ses_ingredients["ingredientRegionId"].apply(
                            d.couleur_provenance
                        )
                        st.dataframe(
                            ses_ingredients[["Provenance", "ingredientName", "quantity"]].rename(
                                columns={"ingredientName": "Ingrédient", "quantity": "Quantité"}
                            ),
                            hide_index=True,
                            width="stretch",
                        )

with onglet_profils:
    profils = d.charger_profils()
    metiers_recolte = d.metiers_recolte()

    effectifs_recolte = profils["Métiers de récolte"].str.split(", ").explode().value_counts()
    for colonne, nom in zip(st.columns(len(metiers_recolte)), sorted(metiers_recolte["name"])):
        colonne.metric(nom, int(effectifs_recolte.get(nom, 0)))

    filtre_recolte = st.selectbox("Filtrer par récolte", ["Tous"] + sorted(metiers_recolte["name"]))
    if filtre_recolte != "Tous":
        profils = profils[profils["Métiers de récolte"].str.contains(filtre_recolte)]

    profils_tries = profils.sort_values("Rôle", key=lambda col: col != "Principal")

    for _, profil in profils_tries.iterrows():
        with st.container(border=True):
            st.markdown(
                "<div style='display:flex; justify-content:space-between; "
                "align-items:center; gap:1rem;'>"
                f"<span><strong>{profil['Pseudo']}</strong></span>"
                f"<span style='white-space:nowrap;'>{profil['Rôle']}</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.caption(f"Artisanat : {profil['Artisanat']} · Récolte : {profil['Métiers de récolte']}")

with onglet_recolte:
    recoltables = d.objets_recoltables()
    sous_onglets_recolte = st.tabs(list(d.ACTIVITES_RECOLTE.values()))

    for sous_onglet, activite in zip(sous_onglets_recolte, d.ACTIVITES_RECOLTE):
        with sous_onglet:
            objets_activite = recoltables[recoltables["gatheringType"] == activite].copy()
            objets_activite["Métiers"] = objets_activite["id"].apply(
                lambda item_id: d.metiers_utilisateurs(item_id, ingredients, metiers)
            )

            filtre_metier = st.selectbox(
                "Filtrer par métier",
                ["Tous"] + sorted(metiers["name"]),
                key=f"filtre_metier_{activite}",
            )
            if filtre_metier != "Tous":
                objets_activite = objets_activite[objets_activite["Métiers"].str.contains(filtre_metier)]

            st.dataframe(
                objets_activite[["name", "rarityLabel", "Métiers"]].rename(
                    columns={"name": "Ingrédient", "rarityLabel": "Rareté"}
                ),
                hide_index=True,
                width="stretch",
            )
