"""Wiki du contenu joueur de KINGDOM : objets, recettes, lieux, classes, PvP."""
import pandas as pd
import streamlit as st

import donnees as d

RUBRIQUES = ["Objets", "Recettes", "Outils", "Consommables", "Lieux", "Classes & Métiers", "PvP"]


def _filtre_texte(df: pd.DataFrame, colonnes: list[str], recherche: str) -> pd.DataFrame:
    if not recherche:
        return df
    masque = pd.Series(False, index=df.index)
    for colonne in colonnes:
        masque |= df[colonne].astype(str).str.contains(recherche, case=False, na=False)
    return df[masque]


def _section_objets() -> None:
    objets = d.objets()
    col_recherche, col_categorie, col_rarete = st.columns([2, 1, 1])
    recherche = col_recherche.text_input("Rechercher un objet", key="wiki_objets_recherche")
    categorie = col_categorie.selectbox(
        "Catégorie", ["Toutes"] + sorted(objets["categoryLabel"].dropna().unique()), key="wiki_objets_categorie"
    )
    rarete = col_rarete.selectbox(
        "Rareté", ["Toutes"] + sorted(objets["rarityLabel"].dropna().unique()), key="wiki_objets_rarete"
    )

    resultat = _filtre_texte(objets, ["name", "description"], recherche)
    if categorie != "Toutes":
        resultat = resultat[resultat["categoryLabel"] == categorie]
    if rarete != "Toutes":
        resultat = resultat[resultat["rarityLabel"] == rarete]

    st.dataframe(
        resultat[["emoji", "name", "categoryLabel", "rarityLabel", "baseValue", "regionLabel", "description"]].rename(
            columns={
                "emoji": "",
                "name": "Objet",
                "categoryLabel": "Catégorie",
                "rarityLabel": "Rareté",
                "baseValue": "Valeur",
                "regionLabel": "Région",
                "description": "Description",
            }
        ).fillna(""),
        hide_index=True,
        width="stretch",
    )
    st.caption(f"{len(resultat)} objet(s) sur {len(objets)}.")


def _section_recettes() -> None:
    recettes = d.recettes()
    ingredients = d.ingredients_recettes()

    station = st.selectbox("Station", ["Toutes"] + sorted(recettes["station"].dropna().unique()), key="wiki_recette_station")
    recherche = st.text_input("Rechercher une recette", key="wiki_recette_recherche")

    resultat = _filtre_texte(recettes, ["resultName"], recherche)
    if station != "Toutes":
        resultat = resultat[resultat["station"] == station]

    for _, recette in resultat.iterrows():
        titre = f"{recette['resultName']} — {recette['requiredJobName']} niv. {recette['requiredJobLevel']}"
        with st.expander(titre):
            ses_ingredients = ingredients[ingredients["recipeId"] == recette["id"]]
            st.dataframe(
                ses_ingredients[["ingredientName", "quantity", "ingredientCategory"]].rename(
                    columns={"ingredientName": "Ingrédient", "quantity": "Quantité", "ingredientCategory": "Catégorie"}
                ),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                f"Résultat : {recette['resultQuantity']} × {recette['resultName']} "
                f"({recette['resultRarity']}) — ratio valeur/coût {recette['valueToCostRatio']:.2f}"
            )
    st.caption(f"{len(resultat)} recette(s) sur {len(recettes)}.")


def _section_outils() -> None:
    outils = d.outils()
    st.dataframe(
        outils[
            ["name", "rarity", "requiredJobName", "requiredJobLevel", "xpMultiplier", "qualityShift", "recoveryReduction"]
        ].rename(
            columns={
                "name": "Outil",
                "rarity": "Rareté",
                "requiredJobName": "Métier",
                "requiredJobLevel": "Niveau requis",
                "xpMultiplier": "Multiplicateur XP",
                "qualityShift": "Bonus qualité",
                "recoveryReduction": "Réduction récup.",
            }
        ).fillna(""),
        hide_index=True,
        width="stretch",
    )


def _section_consommables() -> None:
    consommables = d.consommables()
    st.dataframe(
        consommables[
            ["name", "category", "consumableType", "xpMultiplier", "rareChance", "travelTimeReduction"]
        ].rename(
            columns={
                "name": "Consommable",
                "category": "Catégorie",
                "consumableType": "Type d'effet",
                "xpMultiplier": "Multiplicateur XP",
                "rareChance": "Bonus rareté",
                "travelTimeReduction": "Réduction voyage",
            }
        ).fillna(""),
        hide_index=True,
        width="stretch",
    )


def _section_lieux() -> None:
    lieux = d.lieux()
    butin = d.butin_lieux()
    regions = ["Toutes"] + sorted(lieux["regionLabel"].dropna().unique())
    region = st.selectbox("Région", regions, key="wiki_lieux_region")

    lieux_actifs = lieux[lieux["gatheringEnabled"] == True]  # noqa: E712
    if region != "Toutes":
        lieux_actifs = lieux_actifs[lieux_actifs["regionLabel"] == region]

    for _, lieu in lieux_actifs.iterrows():
        with st.expander(f"{lieu['emoji']} {lieu['name']} — {lieu['regionLabel']} ({lieu['activityLabel']})"):
            butin_lieu = butin[butin["locationId"] == lieu["id"]]
            st.dataframe(
                butin_lieu[["itemName", "rarity", "resourceScope", "minQuantity", "maxQuantity"]].rename(
                    columns={
                        "itemName": "Ressource",
                        "rarity": "Rareté",
                        "resourceScope": "Portée",
                        "minQuantity": "Qté min",
                        "maxQuantity": "Qté max",
                    }
                ),
                hide_index=True,
                width="stretch",
            )


def _section_classes_metiers() -> None:
    st.subheader("Classes")
    st.dataframe(
        d.classes()[["emoji", "name", "primaryWeaponType", "description"]].rename(
            columns={"emoji": "", "name": "Classe", "primaryWeaponType": "Arme", "description": "Description"}
        ),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Métiers et paliers")
    paliers = d.paliers_metiers()
    for _, metier in d.metiers().iterrows():
        with st.expander(f"{metier['emoji']} {metier['name']} ({metier['type']})"):
            st.write(metier["description"])
            ses_paliers = paliers[paliers["jobId"] == metier["id"]]
            if not ses_paliers.empty:
                st.dataframe(
                    ses_paliers[["level", "label"]].rename(columns={"level": "Niveau", "label": "Déblocage"}),
                    hide_index=True,
                    width="stretch",
                )


def _section_pvp() -> None:
    classes_pvp = d.pvp_classes()
    classe_choisie = st.selectbox("Classe", classes_pvp["className"], key="wiki_pvp_classe")
    ligne_classe = classes_pvp[classes_pvp["className"] == classe_choisie].iloc[0]

    st.dataframe(
        classes_pvp[classes_pvp["className"] == classe_choisie][
            ["maxHp", "attack", "defense", "critChance", "critMultiplier", "dodgeChance", "accuracy", "speed"]
        ].rename(
            columns={
                "maxHp": "PV max",
                "attack": "Attaque",
                "defense": "Défense",
                "critChance": "Chance crit.",
                "critMultiplier": "Multiplicateur crit.",
                "dodgeChance": "Esquive",
                "accuracy": "Précision",
                "speed": "Vitesse",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Compétences")
    competences = d.pvp_competences()
    st.dataframe(
        competences[competences["classId"] == ligne_classe["classId"]][
            ["kind", "name", "resourceCost", "cooldown", "unlockLevel", "description"]
        ].rename(
            columns={
                "kind": "Type",
                "name": "Compétence",
                "resourceCost": f"Coût ({ligne_classe['resourceLabel']})",
                "cooldown": "Cooldown",
                "unlockLevel": "Niveau requis",
                "description": "Effet",
            }
        ),
        hide_index=True,
        width="stretch",
    )

    st.subheader("Passif")
    passifs = d.pvp_passifs()
    passif_classe = passifs[passifs["classId"] == ligne_classe["classId"]]
    if not passif_classe.empty:
        st.markdown(f"**{passif_classe.iloc[0]['name']}** — {passif_classe.iloc[0]['description']}")

    st.subheader("Équipement")
    equipements = d.pvp_equipements()
    equip_classe = equipements[equipements["classId"] == ligne_classe["classId"]]
    slot = st.selectbox("Emplacement", ["Tous"] + sorted(equip_classe["slot"].dropna().unique()), key="wiki_pvp_slot")
    if slot != "Tous":
        equip_classe = equip_classe[equip_classe["slot"] == slot]
    colonnes_stats = ["itemName", "slot", "rarity", "attack", "defense", "maxHp", "critChance", "dodgeChance", "accuracy"]
    st.dataframe(
        equip_classe[colonnes_stats].rename(
            columns={
                "itemName": "Objet",
                "slot": "Emplacement",
                "rarity": "Rareté",
                "attack": "Attaque",
                "defense": "Défense",
                "maxHp": "PV max",
                "critChance": "Crit.",
                "dodgeChance": "Esquive",
                "accuracy": "Précision",
            }
        ).fillna(""),
        hide_index=True,
        width="stretch",
    )


_RENDUS = {
    "Objets": _section_objets,
    "Recettes": _section_recettes,
    "Outils": _section_outils,
    "Consommables": _section_consommables,
    "Lieux": _section_lieux,
    "Classes & Métiers": _section_classes_metiers,
    "PvP": _section_pvp,
}


def afficher() -> None:
    rubrique = st.radio("Rubrique", RUBRIQUES, horizontal=True, key="wiki_rubrique")
    st.divider()
    _RENDUS[rubrique]()
