"""Accès aux données du classeur KINGDOM (NEW_MMORPG_Game_Data.xlsx)."""
from pathlib import Path

import pandas as pd
import streamlit as st

CHEMIN_CLASSEUR = Path(__file__).resolve().parent.parent / "NEW_MMORPG_Game_Data.xlsx"

COULEUR_PAR_REGION = {"RED": "🔴", "BLUE": "🔵", "GREEN": "🟢", "PURPLE": "🟣"}
COULEUR_COMMUNE = "⚪"


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


def couleur_provenance(region_id: str | None) -> str:
    """Emoji couleur de la région d'origine d'un ingrédient, ⚪ si commun (global)."""
    if pd.isna(region_id):
        return COULEUR_COMMUNE
    return COULEUR_PAR_REGION.get(region_id, COULEUR_COMMUNE)
