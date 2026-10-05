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

onglet_metiers, onglet_profils, onglet_recolte = st.tabs(["Métiers", "Profils", "Ingrédients de récolte"])

with onglet_metiers:
    sous_onglets = st.tabs([m["name"] for _, m in metiers.iterrows()])

    for sous_onglet, (_, metier) in zip(sous_onglets, metiers.iterrows()):
        with sous_onglet:
            recettes_metier = recettes[recettes["station"] == metier["station"]].sort_values("requiredJobLevel")
            for _, recette in recettes_metier.iterrows():
                titre = f"Niveau {recette['requiredJobLevel']} — {recette['resultName']} (+{int(recette['xp'])} XP)"
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
    st.write("Bientôt")

with onglet_recolte:
    recoltables = d.objets_recoltables()
    sous_onglets_recolte = st.tabs(list(d.ACTIVITES_RECOLTE.values()))

    for sous_onglet, activite in zip(sous_onglets_recolte, d.ACTIVITES_RECOLTE):
        with sous_onglet:
            objets_activite = recoltables[recoltables["gatheringType"] == activite].copy()
            objets_activite["Métiers"] = objets_activite["id"].apply(
                lambda item_id: d.metiers_utilisateurs(item_id, ingredients, metiers)
            )
            st.dataframe(
                objets_activite[["name", "rarityLabel", "Métiers"]].rename(
                    columns={"name": "Ingrédient", "rarityLabel": "Rareté"}
                ),
                hide_index=True,
                width="stretch",
            )
