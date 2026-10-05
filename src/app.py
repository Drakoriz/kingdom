"""Recettes d'artisanat de KINGDOM, par métier."""
import streamlit as st

import donnees as d

st.set_page_config(page_title="KINGDOM — Recettes", page_icon="🔨", layout="wide")

st.title("🔨 KINGDOM — Recettes d'artisanat")

onglet_metiers, onglet_profils = st.tabs(["🔨 Métiers", "👥 Profils"])

with onglet_metiers:
    recettes = d.recettes()
    ingredients = d.ingredients_recettes()
    metiers = d.metiers_artisanat()
    objets_par_id = d.objets().set_index("id")
    equipements = d.pvp_equipements()

    sous_onglets = st.tabs([f"{m['emoji']} {m['name']}" for _, m in metiers.iterrows()])

    for sous_onglet, (_, metier) in zip(sous_onglets, metiers.iterrows()):
        with sous_onglet:
            recettes_metier = recettes[recettes["station"] == metier["station"]].sort_values("requiredJobLevel")
            for _, recette in recettes_metier.iterrows():
                titre = f"Niveau {recette['requiredJobLevel']} — {recette['resultName']}"
                effet = d.effet_objet(recette["resultItemId"], objets_par_id, equipements)
                if effet:
                    titre += f" : {effet}"
                with st.expander(titre):
                    ses_ingredients = ingredients[ingredients["recipeId"] == recette["id"]].copy()
                    ses_ingredients["Provenance"] = ses_ingredients["ingredientRegionId"].apply(d.couleur_provenance)
                    st.dataframe(
                        ses_ingredients[["Provenance", "ingredientName", "quantity"]].rename(
                            columns={"ingredientName": "Ingrédient", "quantity": "Quantité"}
                        ),
                        hide_index=True,
                        width="stretch",
                    )

with onglet_profils:
    st.write("Bientôt")
