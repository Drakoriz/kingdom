"""Accès aux données du classeur KINGDOM (NEW_MMORPG_Game_Data.xlsx)."""
from pathlib import Path

import pandas as pd
import streamlit as st

CHEMIN_CLASSEUR = Path(__file__).resolve().parent.parent / "NEW_MMORPG_Game_Data.xlsx"
CHEMIN_PROFILS = Path(__file__).resolve().parent / "data" / "profils_equipe.csv"

REGION_EQUIPE = "GREEN"
MAISON_EQUIPE_ID = "house3"

COLONNES_PROFILS = [
    "Pseudo Discord",
    "Classe",
    "Artisanat",
    "Rôle dans l'équipe",
    "Niveau le plus haut",
    "Notes",
]


@st.cache_data
def charger_feuille(nom_feuille: str) -> pd.DataFrame:
    """Chaque feuille du classeur a 3 lignes d'en-tête (titre, description, vide)."""
    return pd.read_excel(CHEMIN_CLASSEUR, sheet_name=nom_feuille, header=3)


def classes() -> pd.DataFrame:
    return charger_feuille("Classes")


def metiers() -> pd.DataFrame:
    return charger_feuille("Jobs")


def maisons_regions() -> pd.DataFrame:
    return charger_feuille("House Regions")


def raretes() -> pd.DataFrame:
    return charger_feuille("Rarities")


def pvp_classes() -> pd.DataFrame:
    return charger_feuille("PvP Classes")


def lieux() -> pd.DataFrame:
    return charger_feuille("Locations")


def butin_lieux() -> pd.DataFrame:
    return charger_feuille("Location Loot")


def lieux_equipe() -> pd.DataFrame:
    df = lieux()
    return df[df["regionId"] == REGION_EQUIPE]


def ressources_regionales_equipe() -> pd.DataFrame:
    """Ressources exclusives à la région Verte : revendables ×1.2 hors région."""
    df = butin_lieux()
    return df[(df["locationRegionId"] == REGION_EQUIPE) & (df["resourceScope"] == "REGIONAL")]


def synergies_classe_artisanat() -> pd.DataFrame:
    c = classes()[["name", "emoji", "synergyCraftJobId"]]
    j = metiers()[["id", "name", "emoji"]].rename(
        columns={"name": "artisanat", "emoji": "artisanat_emoji"}
    )
    fusion = c.merge(j, left_on="synergyCraftJobId", right_on="id")
    return fusion[["emoji", "name", "artisanat_emoji", "artisanat"]].rename(
        columns={"emoji": "", "name": "Classe", "artisanat_emoji": " ", "artisanat": "Artisanat synergique"}
    )


def charger_profils() -> pd.DataFrame:
    if CHEMIN_PROFILS.exists():
        return pd.read_csv(CHEMIN_PROFILS)
    return pd.DataFrame(columns=COLONNES_PROFILS)


def sauvegarder_profils(df: pd.DataFrame) -> None:
    CHEMIN_PROFILS.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CHEMIN_PROFILS, index=False)
