"""Accès aux données du classeur KINGDOM (NEW_MMORPG_Game_Data.xlsx)."""
import json
from pathlib import Path

import pandas as pd
import pulp
import streamlit as st

CHEMIN_CLASSEUR = Path(__file__).resolve().parent.parent / "NEW_MMORPG_Game_Data.xlsx"
CHEMIN_PROFILS = Path(__file__).resolve().parent / "data" / "profils_equipe.csv"
CHEMIN_STOCK = Path(__file__).resolve().parent / "data" / "stock_marchand.csv"

COLONNES_PROFILS = ["Pseudo", "Artisanat", "Métiers de récolte", "Rôle"]

COULEUR_PAR_REGION = {"RED": "🔴", "BLUE": "🔵", "GREEN": "🟢", "PURPLE": "🟣"}
COULEUR_COMMUNE = "⚪"

ACTIVITES_RECOLTE = {"fishing": "Pêche", "mining": "Minage", "woodcutting": "Coupe", "farming": "Culture"}
ORDRE_RARETE = ["COMMON", "RARE", "EPIC", "LEGENDARY"]
MAISON_JOUEUR = "GREEN"

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


def libelles_rarete() -> dict:
    """Libellé français + emoji de chaque rareté (feuille Rarities), ex. {"COMMON": "⚪ Commun"}."""
    raretes = charger_feuille("Rarities")
    return {row["id"]: f"{row['emoji']} {row['label']}" for _, row in raretes.iterrows()}


def courbe_recolte() -> pd.DataFrame:
    """Probabilité de chaque rareté selon le niveau du métier de récolte (feuille Gather Curve),
    pour voir comment les chances évoluent en montant de niveau (valable pour tous les métiers de récolte)."""
    courbe = charger_feuille("Gather Curve")
    return courbe.pivot(index="level", columns="rarity", values="weightPercent")[ORDRE_RARETE]


def economie_config() -> pd.Series:
    """Paramètres économiques du jeu (taxes, taux de revente...), indexés par chemin de config."""
    return charger_feuille("Economy Config").set_index("path")["value"]


def multiplicateur_regional(region_id: str | None, maison: str = MAISON_JOUEUR) -> float:
    """Bonus/malus de revente au marchand royal selon l'origine régionale d'une ressource par
    rapport à sa propre maison (Economy Config, regionalTrade.*) : une ressource étrangère se
    revend plus cher (x1.2) qu'une ressource de sa propre maison ou universelle."""
    economie = economie_config()
    if pd.isna(region_id):
        return float(economie["regionalTrade.neutralMultiplier"])
    if region_id == maison:
        return float(economie["regionalTrade.homeMultiplier"])
    return float(economie["regionalTrade.foreignMultiplier"])


def niveaux_demande() -> list[dict]:
    """Paliers de demande du marchand royal (Economy Config, royalShop.stockDemand), qui modulent
    le prix de revente des ressources BRUTES selon le stock actuel du marchand pour cet objet (les
    objets craftés n'y sont pas soumis, ils se vendent toujours au taux plein)."""
    economie = economie_config()
    niveaux, i = [], 0
    while f"royalShop.stockDemand[{i}].multiplier" in economie.index:
        niveaux.append({
            "upTo": economie.get(f"royalShop.stockDemand[{i}].upTo"),
            "label": economie[f"royalShop.stockDemand[{i}].label"],
            "emoji": economie[f"royalShop.stockDemand[{i}].emoji"],
            "multiplicateur": float(economie[f"royalShop.stockDemand[{i}].multiplier"]),
        })
        i += 1
    return niveaux


def palier_pour_stock(stock: float) -> dict:
    """Palier de demande correspondant à un niveau de stock donné (le dernier palier, sans upTo,
    sert de catégorie `Surstock` au-delà du dernier seuil)."""
    for niveau in niveaux_demande():
        if pd.isna(niveau["upTo"]) or stock <= niveau["upTo"]:
            return niveau
    return niveaux_demande()[-1]


def multiplicateur_demande_stock(stock_actuel: float | None) -> float:
    """Multiplicateur de demande pour un objet dont on connaît le stock actuel au marchand ; 1.0
    (neutre) si le stock est inconnu, faute de relevé."""
    if stock_actuel is None or pd.isna(stock_actuel):
        return 1.0
    return palier_pour_stock(stock_actuel)["multiplicateur"]


def parser_stock_marchand(texte: str) -> dict:
    """Parse un relevé de stock du marchand collé depuis Discord (lignes '* Nom : 123' ou
    '* Nom : 2 529'), en ignorant les en-têtes de rareté et les valeurs manquantes."""
    stock = {}
    for ligne in texte.splitlines():
        ligne = ligne.strip().lstrip("*").strip()
        if " : " not in ligne:
            continue
        nom, valeur = ligne.rsplit(" : ", 1)
        valeur = "".join(c for c in valeur if c.isdigit())
        if valeur:
            stock[nom.strip()] = int(valeur)
    return stock


def charger_stock_marchand() -> dict:
    if CHEMIN_STOCK.exists():
        df = pd.read_csv(CHEMIN_STOCK)
        return dict(zip(df["nom"], df["quantite"]))
    return {}


def sauvegarder_stock_marchand(stock: dict) -> None:
    pd.DataFrame(sorted(stock.items()), columns=["nom", "quantite"]).to_csv(CHEMIN_STOCK, index=False)


def rentabilite_vente_stock(probabilites: dict, taux_revente: float, stock: dict) -> pd.DataFrame:
    """Comme rentabilite_vente, mais avec le palier de demande réel de chaque ressource brute
    (déduit de son stock actuel au marchand) plutôt qu'un palier choisi manuellement."""
    vendables = objets_recoltables()
    vendables = vendables[vendables["shopSellable"] == True].copy()
    vendables["multiplicateurRegional"] = vendables["regionId"].apply(multiplicateur_regional)
    vendables["stockActuel"] = vendables["name"].map(stock)
    vendables["multiplicateurDemande"] = vendables["stockActuel"].apply(multiplicateur_demande_stock)
    vendables["prixVente"] = (
        vendables["baseValue"] * taux_revente * vendables["multiplicateurRegional"] * vendables["multiplicateurDemande"]
    )
    vendables["orParEffort"] = vendables.apply(lambda r: r["prixVente"] * probabilites.get(r["rarity"], 1), axis=1)
    return vendables.sort_values("orParEffort", ascending=False)


def benefice_craft_vs_brut(
    recettes: pd.DataFrame, ingredients: pd.DataFrame, objets_par_id: pd.DataFrame, taux_revente: float, stock: dict
) -> pd.DataFrame:
    """Pour chaque recette vendable, compare la valeur de vente actuelle de ses matériaux bruts
    (décomposés jusqu'au bout, chacun à son palier de stock réel) à la valeur de l'objet crafté
    (toujours au taux plein, non soumis au stock). Bénéfice positif = plus worth de crafter
    maintenant que de vendre les bruts tels quels."""
    objets_par_nom = objets_par_id.reset_index().set_index("name")
    lignes = []
    for _, recette in recettes.iterrows():
        resultat = objets_par_id.loc[recette["resultItemId"]]
        if not resultat["shopSellable"]:
            continue
        prix_crafte = resultat["baseValue"] * taux_revente * recette["resultQuantity"]
        composants = composants_bruts_recette(recette["id"], 1, ingredients)
        valeur_brute = 0.0
        for nom, qte in composants.items():
            item = objets_par_nom.loc[nom]
            valeur_brute += (
                qte * item["baseValue"] * taux_revente
                * multiplicateur_regional(item["regionId"])
                * multiplicateur_demande_stock(stock.get(nom))
            )
        lignes.append({
            "id": recette["id"],
            "nom": recette["resultName"],
            "station": recette["station"],
            "prixCrafte": prix_crafte,
            "valeurBrute": valeur_brute,
            "benefice": prix_crafte - valeur_brute,
        })
    return pd.DataFrame(lignes).sort_values("benefice", ascending=False)


def rentabilite_vente(probabilites: dict, taux_revente: float, multiplicateur_demande: float = 1.0) -> pd.DataFrame:
    """Rentabilité de revente au marchand royal des ressources récoltables : prix de vente
    (baseValue x taux de revente x bonus régional x demande actuelle) pondéré par la probabilité
    de rareté, pour comparer l'or gagné par effort de récolte entre objets communs et rares."""
    vendables = objets_recoltables()
    vendables = vendables[vendables["shopSellable"] == True].copy()
    vendables["multiplicateurRegional"] = vendables["regionId"].apply(multiplicateur_regional)
    vendables["prixVente"] = vendables["baseValue"] * taux_revente * vendables["multiplicateurRegional"] * multiplicateur_demande
    vendables["orParEffort"] = vendables.apply(lambda r: r["prixVente"] * probabilites.get(r["rarity"], 1), axis=1)
    return vendables.sort_values("orParEffort", ascending=False)


def rentabilite_vente_craftee(
    recettes: pd.DataFrame,
    ingredients: pd.DataFrame,
    probabilites: dict,
    taux_revente: float,
    objets_par_id: pd.DataFrame,
    multiplicateur_demande: float = 1.0,
) -> pd.DataFrame:
    """Rentabilité de revente au marchand royal des objets craftés : prix de vente (baseValue x
    taux de revente x bonus régional x demande actuelle) divisé par l'effort de récolte nécessaire
    à leur fabrication (récursif, jusqu'aux matériaux bruts), pour comparer avec la rentabilité des
    ressources brutes. Les objets craftés n'ont pas de région propre (bonus toujours neutre)."""
    craftes = recettes.copy()
    craftes["shopSellable"] = craftes["resultItemId"].map(objets_par_id["shopSellable"])
    craftes["baseValue"] = craftes["resultItemId"].map(objets_par_id["baseValue"])
    craftes["rarityLabel"] = craftes["resultItemId"].map(objets_par_id["rarityLabel"])
    craftes["regionId"] = craftes["resultItemId"].map(objets_par_id["regionId"])
    craftes = craftes[craftes["shopSellable"] == True].copy()
    craftes["multiplicateurRegional"] = craftes["regionId"].apply(multiplicateur_regional)
    craftes["prixVente"] = (
        craftes["baseValue"] * taux_revente * craftes["resultQuantity"] * craftes["multiplicateurRegional"] * multiplicateur_demande
    )
    craftes["effort"] = craftes["id"].apply(lambda rid: effort_recette(rid, ingredients, probabilites))
    craftes["orParEffort"] = craftes.apply(lambda r: efficacite_xp(r["prixVente"], r["effort"]), axis=1)
    return craftes.sort_values("orParEffort", ascending=False)


def composants_bruts(
    item_id: str, quantite: float, nom: str, ingredients: pd.DataFrame, vus: frozenset = frozenset()
) -> dict:
    """Décompose `quantite` unités de `item_id` en matériaux bruts (non craftés) : si l'objet est
    lui-même une recette (ex: Lingot de fer), redescend sur ses propres ingrédients au lieu de
    s'arrêter à lui."""
    sous_recette = ingredients[ingredients["recipeId"] == item_id]
    if sous_recette.empty or item_id in vus:
        return {nom: quantite}
    quantite_produite = sous_recette["resultQuantity"].iloc[0]
    nb_crafts = quantite / quantite_produite
    composants = {}
    for _, ligne in sous_recette.iterrows():
        for cle, valeur in composants_bruts(
            ligne["ingredientItemId"], ligne["quantity"] * nb_crafts, ligne["ingredientName"], ingredients, vus | {item_id}
        ).items():
            composants[cle] = composants.get(cle, 0) + valeur
    return composants


def composants_bruts_recette(recipe_id: str, quantite: float, ingredients: pd.DataFrame) -> dict:
    """Matériaux bruts (non craftés) nécessaires pour fabriquer `quantite` fois une recette, en
    descendant récursivement dans les ingrédients eux-mêmes craftés (ex: lingots)."""
    composants = {}
    for _, ligne in ingredients[ingredients["recipeId"] == recipe_id].iterrows():
        for nom, qte in composants_bruts(
            ligne["ingredientItemId"], ligne["quantity"] * quantite, ligne["ingredientName"], ingredients
        ).items():
            composants[nom] = composants.get(nom, 0) + qte
    return composants


def cout_brut_recette(recipe_id: str, ingredients: pd.DataFrame, valeur_par_nom: pd.Series, taux_achat: float) -> float:
    """Coût pour acheter au marchand royal les ingrédients listés directement dans la recette
    (sans décomposer les intermédiaires comme les lingots)."""
    lignes = ingredients[ingredients["recipeId"] == recipe_id]
    return sum(ligne["quantity"] * valeur_par_nom[ligne["ingredientName"]] * taux_achat for _, ligne in lignes.iterrows())


def cout_production_recette(recipe_id: str, ingredients: pd.DataFrame, valeur_par_nom: pd.Series, taux_achat: float) -> float:
    """Coût pour acheter au marchand royal uniquement les matériaux bruts (décomposés jusqu'au bout),
    à la place de les récolter soi-même."""
    composants = composants_bruts_recette(recipe_id, 1, ingredients)
    return sum(qte * valeur_par_nom[nom] * taux_achat for nom, qte in composants.items())


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
