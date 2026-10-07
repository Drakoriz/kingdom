"""Accès aux données du classeur KINGDOM (NEW_MMORPG_Game_Data.xlsx)."""
import json
from pathlib import Path

import pandas as pd
import pulp
import streamlit as st

CHEMIN_CLASSEUR = Path(__file__).resolve().parent.parent / "NEW_MMORPG_Game_Data.xlsx"
CHEMIN_PROFILS = Path(__file__).resolve().parent / "data" / "profils_equipe.csv"

COLONNES_PROFILS = ["Pseudo", "Artisanat", "Métiers de récolte", "Rôle"]

COULEUR_PAR_REGION = {"RED": "🔴", "BLUE": "🔵", "GREEN": "🟢", "PURPLE": "🟣"}
COULEUR_COMMUNE = "⚪"

ACTIVITES_RECOLTE = {"fishing": "Pêche", "mining": "Minage", "woodcutting": "Coupe", "farming": "Culture"}
ORDRE_RARETE = ["COMMON", "RARE", "EPIC", "LEGENDARY"]

LIBELLES_SLOTS = {"WEAPON": "Arme", "SHIELD": "Bouclier", "ARMOR": "Armure", "ACCESSORY": "Accessoire"}

LIBELLES_CATEGORIES = {
    "ore": "Minerai",
    "wood": "Bois",
    "fish": "Poisson",
    "plant": "Plante",
    "material": "Matériau",
    "tool": "Outil",
    "food": "Nourriture",
    "potion": "Potion",
    "weapon": "Arme",
    "armor": "Armure",
    "accessory": "Accessoire",
}

LIBELLES_EFFETS = {
    "xpMultiplier": lambda v: f"+{round((v - 1) * 100)} % XP",
    "quantityChance": lambda v: f"+{round(v * 100)} % chance de quantité bonus",
    "recoveryReduction": lambda v: f"-{round(v * 100)} % récupération",
    "rareChance": lambda v: f"+{v:g} pts de chance de rareté",
    "travelTimeReduction": lambda v: f"-{round(v * 100)} % temps de voyage",
    "qualityShift": lambda v: f"+{v:g} cran(s) de qualité",
}

LIBELLES_STATS_COMBAT = {
    "attackPct": lambda v: f"+{round(v * 100)} % attaque",
    "defensePct": lambda v: f"+{round(v * 100)} % défense",
    "maxHpPct": lambda v: f"+{round(v * 100)} % PV",
    "critChance": lambda v: f"+{v * 100:.1f} % critique",
    "critMultiplier": lambda v: f"+{round(v * 100)} % dégâts crit.",
    "dodgeChance": lambda v: f"+{v * 100:.1f} % esquive",
    "accuracy": lambda v: f"+{round(v * 100)} % précision",
    "blockPower": lambda v: f"+{round(v * 100)} % blocage",
    "magicPierce": lambda v: f"+{round(v * 100)} % pénétration magique",
    "physicalPierce": lambda v: f"+{round(v * 100)} % pénétration physique",
    "mainStatPct": lambda v: f"+{round(v * 100)} % stat principale",
    "maxHp": lambda v: f"+{v:g} PV",
    "attack": lambda v: f"+{v:g} attaque",
    "defense": lambda v: f"+{v:g} défense",
    "speed": lambda v: f"+{v:g} vitesse",
}


@st.cache_data
def charger_feuille(nom_feuille: str) -> pd.DataFrame:
    """Chaque feuille du classeur a 3 lignes d'en-tête (titre, description, vide)."""
    return pd.read_excel(CHEMIN_CLASSEUR, sheet_name=nom_feuille, header=3)


def metiers_artisanat() -> pd.DataFrame:
    metiers = charger_feuille("Jobs")
    return metiers[metiers["type"] == "crafting"]


def metiers_recolte() -> pd.DataFrame:
    metiers = charger_feuille("Jobs")
    return metiers[metiers["type"] == "gathering"]


def recettes() -> pd.DataFrame:
    return charger_feuille("Recipes")


def ingredients_recettes() -> pd.DataFrame:
    return charger_feuille("Recipe Ingredients")


def objets() -> pd.DataFrame:
    return charger_feuille("Items")


def pvp_equipements() -> pd.DataFrame:
    return charger_feuille("PvP Equip Items")


def couleur_provenance(region_id: str | None) -> str:
    """Emoji couleur de la région d'origine d'un ingrédient, ⚪ si commun (global)."""
    if pd.isna(region_id):
        return COULEUR_COMMUNE
    return COULEUR_PAR_REGION.get(region_id, COULEUR_COMMUNE)


def _traduire_json(valeur_json: str | None, libelles: dict) -> str | None:
    if pd.isna(valeur_json):
        return None
    valeurs = json.loads(valeur_json)
    parties = [libelles[cle](v) for cle, v in valeurs.items() if cle in libelles]
    return " · ".join(parties) if parties else None


def effet_lisible(effects_json: str | None) -> str | None:
    """Traduit un effectsJson/bonusesJson (ex: {"xpMultiplier":1.03}) en texte lisible."""
    return _traduire_json(effects_json, LIBELLES_EFFETS)


def effet_combat_lisible(stats_json: str | None) -> str | None:
    """Traduit le statsJson d'une pièce d'équipement PvP (ex: {"attackPct":0.1}) en texte lisible."""
    return _traduire_json(stats_json, LIBELLES_STATS_COMBAT)


def effet_objet(item_id: str, objets_par_id: pd.DataFrame, equipements: pd.DataFrame) -> str | None:
    """Cherche l'effet d'un objet : consommable/outil d'abord, sinon équipement PvP."""
    item = objets_par_id.loc[item_id]
    effet = effet_lisible(item["effectsJson"]) or effet_lisible(item["bonusesJson"])
    if effet:
        return effet
    equip = equipements[equipements["itemId"] == item_id].dropna(subset=["offClassRatio"])
    if equip.empty:
        return None
    meilleure_affinite = equip.loc[equip["offClassRatio"].idxmax()]
    return effet_combat_lisible(meilleure_affinite["statsJson"])


def usage_materiau(item_id: str, ingredients: pd.DataFrame) -> str | None:
    """Pour un objet sans effet propre : signale juste qu'il sert à fabriquer autre chose."""
    if (ingredients["ingredientItemId"] == item_id).any():
        return "COMPOSANT"
    return None


def objets_recoltables() -> pd.DataFrame:
    """Ressources brutes obtenables par la pêche, le minage, la coupe ou la culture, triées par rareté."""
    tous_les_objets = objets()
    recoltables = tous_les_objets[tous_les_objets["gatheringType"].isin(ACTIVITES_RECOLTE)].copy()
    recoltables["rarity"] = pd.Categorical(recoltables["rarity"], categories=ORDRE_RARETE, ordered=True)
    return recoltables.sort_values("rarity")


def metiers_utilisateurs(item_id: str, ingredients: pd.DataFrame, metiers_craft: pd.DataFrame) -> str:
    """Liste des métiers d'artisanat qui utilisent cet ingrédient dans une recette."""
    stations_utilisees = ingredients[ingredients["ingredientItemId"] == item_id]["station"].unique()
    noms = sorted(metiers_craft[metiers_craft["station"].isin(stations_utilisees)]["name"])
    return ", ".join(noms) if noms else "Aucun"


def probabilites_rarete() -> dict:
    """Probabilité de drop de chaque rareté (feuille Rarities), pour estimer un coût de récolte."""
    raretes = charger_feuille("Rarities")
    return dict(zip(raretes["id"], raretes["weightPercent"]))


def effort_ingredient(
    item_id: str, quantite: float, rarete: str | None, ingredients: pd.DataFrame, probabilites: dict, vus: frozenset = frozenset()
) -> float:
    """Effort de récolte pour obtenir `quantite` unités de `item_id`. Si l'ingrédient est lui-même
    une recette (ex: Lingot de fer), on descend jusqu'à ses propres ingrédients récoltables."""
    sous_recette = ingredients[ingredients["recipeId"] == item_id]
    if sous_recette.empty or item_id in vus:
        return quantite / probabilites.get(rarete, 1)
    quantite_produite = sous_recette["resultQuantity"].iloc[0]
    cout_unitaire = sum(
        effort_ingredient(
            ligne["ingredientItemId"], ligne["quantity"], ligne["ingredientRarity"], ingredients, probabilites, vus | {item_id}
        )
        for _, ligne in sous_recette.iterrows()
    )
    return quantite * cout_unitaire / quantite_produite


def effort_recette(recipe_id: str, ingredients: pd.DataFrame, probabilites: dict) -> float:
    """Effort de récolte estimé pour une recette : somme sur ses ingrédients de l'effort nécessaire
    pour les obtenir (récursif pour les ingrédients eux-mêmes craftés, ex: Lingot de fer)."""
    ses_ingredients = ingredients[ingredients["recipeId"] == recipe_id]
    return sum(
        effort_ingredient(ligne["ingredientItemId"], ligne["quantity"], ligne["ingredientRarity"], ingredients, probabilites)
        for _, ligne in ses_ingredients.iterrows()
    )


def xp_total_ingredient(
    item_id: str, quantite: float, ingredients: pd.DataFrame, recettes: pd.DataFrame, vus: frozenset = frozenset()
) -> float:
    """XP cumulée en forgeant `quantite` unités de `item_id`, si celui-ci est lui-même une recette
    (ex: forger les lingots de fer rapporte déjà de l'XP, avant même de les utiliser dans l'épée)."""
    sous_recette = ingredients[ingredients["recipeId"] == item_id]
    if sous_recette.empty or item_id in vus:
        return 0.0
    quantite_produite = sous_recette["resultQuantity"].iloc[0]
    nb_crafts = quantite / quantite_produite
    xp_recette = recettes.loc[recettes["id"] == item_id, "xp"].iloc[0]
    xp_ingredients = sum(
        xp_total_ingredient(
            ligne["ingredientItemId"], ligne["quantity"] * nb_crafts, ingredients, recettes, vus | {item_id}
        )
        for _, ligne in sous_recette.iterrows()
    )
    return nb_crafts * xp_recette + xp_ingredients


def xp_total_recette(recipe_id: str, ingredients: pd.DataFrame, recettes: pd.DataFrame) -> float:
    """XP totale réellement gagnée en fabriquant une recette : son propre XP, plus celui de ses
    ingrédients s'ils sont eux-mêmes craftés au lieu d'être directement récoltés."""
    xp_propre = recettes.loc[recettes["id"] == recipe_id, "xp"].iloc[0]
    ses_ingredients = ingredients[ingredients["recipeId"] == recipe_id]
    return xp_propre + sum(
        xp_total_ingredient(ligne["ingredientItemId"], ligne["quantity"], ingredients, recettes)
        for _, ligne in ses_ingredients.iterrows()
    )


def efficacite_xp(xp: float, effort: float) -> float:
    """XP gagné par unité d'effort de récolte (la fabrication elle-même est instantanée)."""
    return xp / effort if effort else float("inf")


def progression_equipements_pvp(equipements: pd.DataFrame, recettes: pd.DataFrame, metiers: pd.DataFrame) -> pd.DataFrame:
    """Tout l'équipement sur-classe par rôle PvP et par emplacement, du plus faible au plus fort,
    avec sa provenance (métier d'artisanat et niveau requis, ou "Non craftable" si obtenu autrement)."""
    sur_classe = equipements[(equipements["offClassRatio"] == 1.0) & equipements["slot"].isin(LIBELLES_SLOTS)].copy()
    sur_classe["rang"] = pd.Categorical(sur_classe["rarity"], categories=ORDRE_RARETE, ordered=True)

    sur_classe = sur_classe.merge(
        recettes[["resultItemId", "station", "requiredJobLevel"]], left_on="itemId", right_on="resultItemId", how="left"
    )
    sur_classe = sur_classe.merge(metiers[["station", "name"]], on="station", how="left")
    sur_classe["provenance"] = sur_classe.apply(
        lambda r: f"{r['name']} niveau {int(r['requiredJobLevel'])}" if pd.notna(r["name"]) else "Non craftable (autre source)",
        axis=1,
    )
    return sur_classe.sort_values(["className", "slot", "requiredJobLevel", "rang"])


def marquer_accessible(progression: pd.DataFrame, niveaux_metiers: dict) -> pd.DataFrame:
    """Ajoute une colonne 'accessible' : vrai si l'objet est non craftable (toujours accessible)
    ou si le métier qui le fabrique a déjà atteint le niveau requis."""
    progression = progression.copy()
    progression["accessible"] = progression.apply(
        lambda r: pd.isna(r["requiredJobLevel"]) or r["requiredJobLevel"] <= niveaux_metiers.get(r["station"], 0),
        axis=1,
    )
    return progression


def materiaux_bruts(station: str, ingredients: pd.DataFrame, recettes: pd.DataFrame, niveau_max: int) -> list[str]:
    """Identifiants des matériaux bruts (non craftés) nécessaires, directement ou indirectement,
    par les recettes d'un métier débloquées jusqu'à un niveau donné."""
    a_explorer = list(recettes[(recettes["station"] == station) & (recettes["requiredJobLevel"] <= niveau_max)]["id"])
    bruts, vus = set(), set()
    while a_explorer:
        item_id = a_explorer.pop()
        if item_id in vus:
            continue
        vus.add(item_id)
        for _, ligne in ingredients[ingredients["recipeId"] == item_id].iterrows():
            ingredient_id = ligne["ingredientItemId"]
            if (ingredients["recipeId"] == ingredient_id).any():
                a_explorer.append(ingredient_id)
            else:
                bruts.add(ingredient_id)
    return sorted(bruts)


def optimiser_xp(
    station: str, niveau_actuel: int, disponibilites: dict, ingredients: pd.DataFrame, recettes: pd.DataFrame
) -> tuple[float, dict]:
    """Alloue les matériaux bruts disponibles (clé = ingredientItemId) entre les recettes d'un
    métier pour maximiser l'XP totale, par programmation linéaire. Un ingrédient lui-même crafté
    (ex: Lingot de fer) est aussi une variable de décision : le solveur choisit de le garder tel
    quel pour son XP propre, ou de le transformer en recette plus avancée, selon ce qui rapporte le
    plus au total."""
    recettes_utilisables = recettes[(recettes["station"] == station) & (recettes["requiredJobLevel"] <= niveau_actuel)]
    ids_recettes = list(recettes_utilisables["id"])
    bruts = materiaux_bruts(station, ingredients, recettes, niveau_actuel)
    conso = ingredients.groupby(["recipeId", "ingredientItemId"])["quantity"].sum()
    quantite_produite = ingredients.groupby("recipeId")["resultQuantity"].first()
    xp_par_recette = recettes_utilisables.set_index("id")["xp"].to_dict()

    probleme = pulp.LpProblem("xp_metier", pulp.LpMaximize)
    x = {rid: pulp.LpVariable(f"craft_{rid}", lowBound=0, cat="Integer") for rid in ids_recettes}
    probleme += pulp.lpSum(x[rid] * xp_par_recette[rid] for rid in ids_recettes)

    for item_id in set(ids_recettes) | set(bruts):
        consomme = pulp.lpSum(x[rid] * conso.get((rid, item_id), 0) for rid in ids_recettes)
        if item_id in ids_recettes:
            probleme += consomme <= x[item_id] * quantite_produite.get(item_id, 1)
        else:
            probleme += consomme <= disponibilites.get(item_id, 0)

    probleme.solve(pulp.PULP_CBC_CMD(msg=False))

    repartition = {rid: int(round(x[rid].value() or 0)) for rid in ids_recettes if (x[rid].value() or 0) > 0.5}
    return pulp.value(probleme.objective) or 0.0, repartition


def charger_profils() -> pd.DataFrame:
    if CHEMIN_PROFILS.exists():
        return pd.read_csv(CHEMIN_PROFILS).fillna("")
    return pd.DataFrame(columns=COLONNES_PROFILS)
