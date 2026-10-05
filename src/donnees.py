"""Accès aux données du classeur KINGDOM (NEW_MMORPG_Game_Data.xlsx)."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

CHEMIN_CLASSEUR = Path(__file__).resolve().parent.parent / "NEW_MMORPG_Game_Data.xlsx"

COULEUR_PAR_REGION = {"RED": "🔴", "BLUE": "🔵", "GREEN": "🟢", "PURPLE": "🟣"}
COULEUR_COMMUNE = "⚪"

LIBELLES_EFFETS = {
    "xpMultiplier": lambda v: f"+{round((v - 1) * 100)} % XP",
    "quantityChance": lambda v: f"+{round(v * 100)} % chance de quantité bonus",
    "recoveryReduction": lambda v: f"-{round(v * 100)} % récupération",
    "rareChance": lambda v: f"+{v:g} pts de chance de rareté",
    "travelTimeReduction": lambda v: f"-{round(v * 100)} % temps de voyage",
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


def couleur_provenance(region_id: str | None) -> str:
    """Emoji couleur de la région d'origine d'un ingrédient, ⚪ si commun (global)."""
    if pd.isna(region_id):
        return COULEUR_COMMUNE
    return COULEUR_PAR_REGION.get(region_id, COULEUR_COMMUNE)


def effet_lisible(effects_json: str | None) -> str | None:
    """Traduit le effectsJson d'un objet (ex: {"xpMultiplier":1.03}) en texte lisible."""
    if pd.isna(effects_json):
        return None
    effets = json.loads(effects_json)
    parties = [LIBELLES_EFFETS[cle](valeur) for cle, valeur in effets.items() if cle in LIBELLES_EFFETS]
    return " · ".join(parties) if parties else None
