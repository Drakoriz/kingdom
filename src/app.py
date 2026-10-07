"""Recettes d'artisanat de KINGDOM, par métier."""
import math

import streamlit as st

import donnees as d

st.set_page_config(page_title="KINGDOM — Recettes", layout="wide")

st.title("KINGDOM — Recettes d'artisanat")
st.caption("Si t'es un rouge ou un bleu qui lit ce message, t'es un gros dog qui pue *crachat*")

recettes = d.recettes()
ingredients = d.ingredients_recettes()
metiers = d.metiers_artisanat()
objets_par_id = d.objets().set_index("id")
equipements = d.pvp_equipements()
probabilites_rarete = d.probabilites_rarete()

(
    onglet_metiers,
    onglet_profils,
    onglet_recolte,
    onglet_progression,
    onglet_calculateur,
    onglet_optimisation,
    onglet_pvp,
    onglet_revente,
) = st.tabs(
    ["Métiers", "Profils", "Ingrédients de récolte", "Progression", "Calculateur XP", "Optimisation", "PvP", "Revente"]
)

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
                rarete = objets_par_id.loc[recette["resultItemId"], "rarityLabel"]
                titre = f"Niveau {recette['requiredJobLevel']} — {recette['resultName']} ({rarete}) (+{int(recette['xp'])} XP)"
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
                        ses_ingredients["Type"] = ses_ingredients["ingredientCategory"].map(d.LIBELLES_CATEGORIES)
                        st.dataframe(
                            ses_ingredients[["Provenance", "ingredientName", "Type", "quantity"]].rename(
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
            objets_activite["Provenance"] = objets_activite["regionId"].apply(d.couleur_provenance)

            recherche = st.text_input("Rechercher un ingrédient", key=f"recherche_{activite}")
            filtre_metier = st.selectbox(
                "Filtrer par métier",
                ["Tous"] + sorted(metiers["name"]),
                key=f"filtre_metier_{activite}",
            )
            if recherche:
                objets_activite = objets_activite[objets_activite["name"].str.contains(recherche, case=False)]
            if filtre_metier != "Tous":
                objets_activite = objets_activite[objets_activite["Métiers"].str.contains(filtre_metier)]

            st.dataframe(
                objets_activite[["Provenance", "name", "rarityLabel", "Métiers"]].rename(
                    columns={"name": "Ingrédient", "rarityLabel": "Rareté"}
                ),
                hide_index=True,
                width="stretch",
            )

with onglet_progression:
    st.caption(
        "Plus le niveau d'un métier de récolte augmente, plus les raretés RARE/EPIC/LEGENDARY "
        "deviennent probables (et COMMON diminue). Cette courbe est la même pour tous les métiers "
        "de récolte (pêche, minage, coupe, culture)."
    )

    courbe = d.courbe_recolte() * 100
    libelles = d.libelles_rarete()
    courbe_affichee = courbe.rename(columns=libelles)

    st.line_chart(courbe_affichee)
    st.dataframe(
        courbe_affichee.round(2).rename_axis("Niveau").reset_index(),
        hide_index=True,
        width="stretch",
    )

with onglet_calculateur:
    niveaux_xp = d.charger_feuille("Levels XP")

    metier_choisi = st.selectbox("Métier", metiers["name"])
    station_choisie = metiers.loc[metiers["name"] == metier_choisi, "station"].iloc[0]

    colonne_actuel, colonne_souhaite = st.columns(2)
    niveau_actuel = colonne_actuel.number_input("Niveau actuel", min_value=1, max_value=50, value=1)
    niveau_souhaite = colonne_souhaite.number_input("Niveau souhaité", min_value=1, max_value=50, value=20)

    if niveau_souhaite <= niveau_actuel:
        st.warning("Le niveau souhaité doit être supérieur au niveau actuel.")
    else:
        xp_actuel = niveaux_xp.loc[niveaux_xp["level"] == niveau_actuel, "totalXpAtStart"].iloc[0]
        xp_souhaite = niveaux_xp.loc[niveaux_xp["level"] == niveau_souhaite, "totalXpAtStart"].iloc[0]
        xp_necessaire = xp_souhaite - xp_actuel

        st.metric(f"XP nécessaire ({metier_choisi} {niveau_actuel} → {niveau_souhaite})", f"{xp_necessaire:,.0f}".replace(",", " "))

        recettes_disponibles = recettes[
            (recettes["station"] == station_choisie) & (recettes["requiredJobLevel"] <= niveau_actuel)
        ].copy()

        if recettes_disponibles.empty:
            st.info("Aucune recette disponible à ce niveau.")
        else:
            recettes_disponibles["effort"] = recettes_disponibles["id"].apply(
                lambda recipe_id: d.effort_recette(recipe_id, ingredients, probabilites_rarete)
            )
            recettes_disponibles["efficacite"] = recettes_disponibles.apply(
                lambda r: d.efficacite_xp(r["xp"], r["effort"]), axis=1
            )
            recettes_disponibles["xp_total"] = recettes_disponibles["id"].apply(
                lambda recipe_id: d.xp_total_recette(recipe_id, ingredients, recettes)
            )
            recettes_disponibles["efficacite_reelle"] = recettes_disponibles.apply(
                lambda r: d.efficacite_xp(r["xp_total"], r["effort"]), axis=1
            )

            top5 = recettes_disponibles.sort_values("efficacite", ascending=False).head(5)
            top5_reel = recettes_disponibles.sort_values("efficacite_reelle", ascending=False).head(5)

            st.write("**Option simple** (XP du craft final uniquement) :")
            for _, recette in top5.iterrows():
                nb_crafts = math.ceil(xp_necessaire / recette["xp"])
                st.markdown(f"- {nb_crafts} × {recette['resultName']} ({recette['efficacite']:.1f} XP/effort)")

            st.write(
                "**Option réaliste** (un ingrédient crafté, comme un lingot, rapporte déjà de l'XP "
                "avant même d'être utilisé dans la recette finale) :"
            )
            for _, recette in top5_reel.iterrows():
                nb_crafts = math.ceil(xp_necessaire / recette["xp_total"])
                composants = d.composants_bruts_recette(recette["id"], nb_crafts, ingredients)
                detail = " + ".join(f"{math.ceil(qte)} {nom}" for nom, qte in composants.items())
                st.markdown(
                    f"- {nb_crafts} × {recette['resultName']} ({detail}) "
                    f"= {recette['xp_total'] * nb_crafts:,.0f} XP ({recette['efficacite_reelle']:.1f} XP/effort)".replace(",", " ")
                )

with onglet_optimisation:
    st.caption(
        "Renseigne ce que l'équipe a récolté cette session : le solveur répartit ces matériaux "
        "entre les recettes (y compris les intermédiaires comme les lingots) pour maximiser l'XP totale."
    )

    metier_opt = st.selectbox("Métier", metiers["name"], key="metier_opt")
    station_opt = metiers.loc[metiers["name"] == metier_opt, "station"].iloc[0]
    niveau_opt = st.number_input("Niveau actuel", min_value=1, max_value=50, value=1, key="niveau_opt")

    bruts = d.materiaux_bruts(station_opt, ingredients, recettes, niveau_opt)
    noms_bruts = ingredients.drop_duplicates(subset="ingredientItemId").set_index("ingredientItemId")["ingredientName"]

    st.write("Matériaux récoltés cette session :")
    disponibilites = {}
    colonnes_dispo = st.columns(4)
    for i, item_id in enumerate(bruts):
        disponibilites[item_id] = colonnes_dispo[i % 4].number_input(
            noms_bruts.get(item_id, item_id), min_value=0, value=0, key=f"dispo_{item_id}"
        )

    if not any(disponibilites.values()):
        st.info("Renseigne au moins un matériau récolté pour lancer l'optimisation.")
    else:
        xp_total_opt, repartition = d.optimiser_xp(station_opt, niveau_opt, disponibilites, ingredients, recettes)
        st.metric("XP total atteignable", f"{xp_total_opt:,.0f}".replace(",", " "))
        if not repartition:
            st.warning("Pas assez de matériaux pour fabriquer quoi que ce soit.")
        else:
            noms_recettes = recettes.set_index("id")["resultName"]
            for rid, nb in sorted(repartition.items(), key=lambda kv: -kv[1]):
                st.markdown(f"- {nb} × {noms_recettes[rid]}")

with onglet_pvp:
    st.caption("Indique le niveau actuel de chaque métier pour voir le meilleur équipement déjà accessible.")
    niveaux_metiers_pvp = {}
    for colonne, (_, metier) in zip(st.columns(len(metiers)), metiers.iterrows()):
        niveaux_metiers_pvp[metier["station"]] = colonne.number_input(
            metier["name"], min_value=1, max_value=50, value=1, key=f"niveau_pvp_{metier['station']}"
        )

    progression_pvp = d.progression_equipements_pvp(equipements, recettes, metiers)
    progression_pvp = d.marquer_accessible(progression_pvp, niveaux_metiers_pvp)
    ordre_slots = list(d.LIBELLES_SLOTS)

    sous_onglets_pvp = st.tabs(sorted(progression_pvp["className"].unique()))
    for sous_onglet, nom_classe in zip(sous_onglets_pvp, sorted(progression_pvp["className"].unique())):
        with sous_onglet:
            items_classe = progression_pvp[progression_pvp["className"] == nom_classe]

            for slot in ordre_slots:
                items_slot = items_classe[items_classe["slot"] == slot]
                if items_slot.empty:
                    continue
                craftables = items_slot[items_slot["station"].notna()]
                meilleur_accessible = craftables[craftables["accessible"]].tail(1)
                id_meilleur = meilleur_accessible["itemId"].iloc[0] if not meilleur_accessible.empty else None

                st.write(f"**{d.LIBELLES_SLOTS[slot]}**")
                for _, item in items_slot.iterrows():
                    effet = d.effet_combat_lisible(item["statsJson"])
                    titre = f"{item['itemName']} ({item['rarity']})"
                    if item["itemId"] == id_meilleur:
                        titre += " — meilleur actuellement"
                    elif item["provenance"] == "Non craftable (autre source)":
                        titre += " — hors artisanat"
                    elif not item["accessible"]:
                        titre += " — à venir"
                    with st.container(border=True):
                        st.markdown(
                            "<div style='display:flex; justify-content:space-between; "
                            "align-items:center; gap:1rem;'>"
                            f"<span>{titre}</span>"
                            f"<span style='white-space:nowrap;'>{item['provenance']}</span>"
                            "</div>",
                            unsafe_allow_html=True,
                        )
                        if effet:
                            st.caption(effet)

                        if item["provenance"] != "Non craftable (autre source)":
                            cle_ouverte_pvp = f"ouvert_pvp_{item['itemId']}"
                            st.session_state.setdefault(cle_ouverte_pvp, False)
                            ouvert_pvp = st.session_state[cle_ouverte_pvp]
                            if st.button(
                                "Masquer les ingrédients" if ouvert_pvp else "Voir les ingrédients",
                                key=f"bouton_pvp_{nom_classe}_{slot}_{item['itemId']}",
                            ):
                                st.session_state[cle_ouverte_pvp] = not ouvert_pvp

                            if st.session_state[cle_ouverte_pvp]:
                                ses_ingredients = ingredients[ingredients["recipeId"] == item["itemId"]].copy()
                                ses_ingredients["Provenance"] = ses_ingredients["ingredientRegionId"].apply(
                                    d.couleur_provenance
                                )
                                ses_ingredients["Type"] = ses_ingredients["ingredientCategory"].map(d.LIBELLES_CATEGORIES)
                                st.dataframe(
                                    ses_ingredients[["Provenance", "ingredientName", "Type", "quantity"]].rename(
                                        columns={"ingredientName": "Ingrédient", "quantity": "Quantité"}
                                    ),
                                    hide_index=True,
                                    width="stretch",
                                )

with onglet_revente:
    economie = d.economie_config()
    taux_revente = float(economie["royalShop.defaultPlayerSellMultiplier"])
    taux_achat = float(economie["royalShop.defaultPlayerBuyMultiplier"])
    taux_taxe = float(economie["market.taxRate"])
    duree_annonce_jours = float(economie["market.listingLifetimeSeconds"]) / 86400

    st.write("**Comment marche l'économie**")
    st.markdown(
        f"- Le marchand royal rachète tout objet vendable à **{taux_revente:.0%}** de sa valeur de base, "
        "taux fixe, identique pour tous les objets (pas de bonus pour les objets rares).\n"
        f"- Acheter au marchand royal coûte **{taux_achat:.0%}** de la valeur de base, modulé par le stock "
        "actuel (forte demande = plus cher, surstock = moins cher).\n"
        f"- Le marché entre joueurs prélève une **taxe de {taux_taxe:.0%}** sur chaque vente, mais permet "
        "de fixer son propre prix, contrairement au taux fixe du marchand royal.\n"
        f"- Une annonce sur le marché reste active **{duree_annonce_jours:.0f} jours** avant d'expirer.\n"
        "- Un objet légendaire vaut plus cher qu'un commun, mais pas proportionnellement à sa rareté : "
        "farmer du commun en volume rapporte souvent plus par effort que chasser le rare (voir le "
        "classement ci-dessous)."
    )

    st.write("**Ressources brutes**")
    rentabilite = d.rentabilite_vente(probabilites_rarete, taux_revente)
    rentabilite["Provenance"] = rentabilite["regionId"].apply(d.couleur_provenance)

    filtre_activite = st.selectbox("Filtrer par activité", ["Toutes"] + list(d.ACTIVITES_RECOLTE.values()))
    if filtre_activite != "Toutes":
        activite_id = next(k for k, v in d.ACTIVITES_RECOLTE.items() if v == filtre_activite)
        rentabilite = rentabilite[rentabilite["gatheringType"] == activite_id]

    st.dataframe(
        rentabilite[["Provenance", "name", "rarityLabel", "prixVente", "orParEffort"]].rename(
            columns={
                "name": "Ingrédient",
                "rarityLabel": "Rareté",
                "prixVente": "Prix de vente",
                "orParEffort": "Or par effort",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    st.write("**Objets craftés**")
    rentabilite_craftee = d.rentabilite_vente_craftee(recettes, ingredients, probabilites_rarete, taux_revente, objets_par_id)
    rentabilite_craftee["Métier"] = rentabilite_craftee["station"].map(metiers.set_index("station")["name"])

    filtre_metier_revente = st.selectbox(
        "Filtrer par métier", ["Tous"] + sorted(metiers["name"]), key="filtre_metier_revente"
    )
    if filtre_metier_revente != "Tous":
        rentabilite_craftee = rentabilite_craftee[rentabilite_craftee["Métier"] == filtre_metier_revente]

    st.dataframe(
        rentabilite_craftee[["Métier", "resultName", "rarityLabel", "prixVente", "orParEffort"]].rename(
            columns={
                "resultName": "Objet",
                "rarityLabel": "Rareté",
                "prixVente": "Prix de vente",
                "orParEffort": "Or par effort",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    objectif_or = st.number_input("Objectif en or", min_value=1, value=15000, step=1000)
    top5_craftes = rentabilite_craftee.sort_values("orParEffort", ascending=False).head(5)
    st.write(f"Pour atteindre {objectif_or:,.0f} or, au choix :".replace(",", " "))
    for _, item in top5_craftes.iterrows():
        nb_crafts = math.ceil(objectif_or / item["prixVente"])
        composants = d.composants_bruts_recette(item["id"], nb_crafts, ingredients)
        detail = " + ".join(f"{math.ceil(qte)} {nom}" for nom, qte in composants.items())
        st.markdown(
            f"- {nb_crafts} × {item['resultName']} ({detail}) "
            f"= {item['prixVente'] * nb_crafts:,.0f} or ({item['orParEffort']:.1f} or/effort)".replace(",", " ")
        )
