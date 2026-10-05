"""Accès aux données du classeur KINGDOM (NEW_MMORPG_Game_Data.xlsx)."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

CHEMIN_CLASSEUR = Path(__file__).resolve().parent.parent / "NEW_MMORPG_Game_Data.xlsx"

COULEUR_PAR_REGION = {"RED": "🔴", "BLUE": "🔵", "GREEN": "🟢", "PURPLE": "🟣"}
COULEUR_COMMUNE = "⚪"

ACTIVITES_RECOLTE = {"fishing": "Pêche", "mining": "Minage", "woodcutting": "Coupe", "farming": "Culture"}
ORDRE_RARETE = ["COMMON", "RARE", "EPIC", "LEGENDARY"]

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


def effort_recette(recipe_id: str, ingredients: pd.DataFrame, probabilites: dict) -> float:
    """Effort de récolte estimé pour une recette : somme(quantité ÷ probabilité de rareté)
    sur ses ingrédients. Plus un ingrédient est rare, plus il faut de tentatives en moyenne."""
    ses_ingredients = ingredients[ingredients["recipeId"] == recipe_id]
    return sum(
        ligne["quantity"] / probabilites.get(ligne["ingredientRarity"], 1) for _, ligne in ses_ingredients.iterrows()
    )


def efficacite_xp(xp: float, effort: float) -> float:
    """XP gagné par unité d'effort de récolte (la fabrication elle-même est instantanée)."""
    return xp / effort if effort else float("inf")
