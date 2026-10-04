"""Tableau de bord Team Verte (Maison III) pour le jeu Discord KINGDOM."""
import streamlit as st

import donnees as d

st.set_page_config(page_title="Team Verte — KINGDOM", page_icon="🟢", layout="wide")

st.title("🟢 Team Verte — Maison III")
st.caption("Tableau de bord stratégique pour l'équipe, basé sur les données du Royaume.")

onglet_info, onglet_strategie, onglet_profils = st.tabs(
    ["ℹ️ Info", "🧭 Stratégie", "👥 Profils de l'équipe"]
)

# ---------------------------------------------------------------- Info
with onglet_info:
    st.header("Le jeu en bref")
    st.markdown(
        """
        **KINGDOM** est un bot économique sur Discord. Chaque joueur a **1 classe** et **1 artisanat**
        exclusifs (16 combinaisons), plus **les 4 métiers de récolte** accessibles à tous en même temps
        (Pêcheur, Mineur, Bûcheron, Fermier), chacun progressant de niveau 1 à 50.

        La **Maison** vient du rôle Discord. Sans Maison, on est **Villageois** libre (neutre, jamais
        visé par la défense territoriale, mais sans entrepôt ni bonus de territoire).
        """
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Classes")
        st.dataframe(
            d.classes()[["emoji", "name", "description"]].rename(
                columns={"emoji": "", "name": "Classe", "description": "Description"}
            ),
            hide_index=True,
            use_container_width=True,
        )
    with col2:
        st.subheader("Métiers")
        st.dataframe(
            d.metiers()[["emoji", "name", "type", "description"]].rename(
                columns={"emoji": "", "name": "Métier", "type": "Type", "description": "Description"}
            ),
            hide_index=True,
            use_container_width=True,
        )

    st.subheader("Les 4 Maisons du Royaume")
    st.dataframe(
        d.maisons_regions().rename(
            columns={
                "houseName": "Maison",
                "regionLabel": "Région",
                "regionId": "Code région",
            }
        )[["Maison", "Région", "Code région"]],
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Nos 4 lieux (Maison III, région Verte)")
    lieux_verte = d.lieux_equipe()
    lieux_actifs = lieux_verte[lieux_verte["gatheringEnabled"] == True]  # noqa: E712
    st.dataframe(
        lieux_actifs[["emoji", "name", "activityLabel", "description"]].rename(
            columns={"emoji": "", "name": "Lieu", "activityLabel": "Activité", "description": "Description"}
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "⚠️ La Tourbière des Damnés est maudite : non accessible pour l'instant (contenu futur)."
    )

    st.subheader("Raretés")
    st.dataframe(
        d.raretes()[["emoji", "label", "weightPercent"]].rename(
            columns={"emoji": "", "label": "Rareté", "weightPercent": "Probabilité (base)"}
        ).assign(**{"Probabilité (base)": lambda df: (df["Probabilité (base)"] * 100).round(2).astype(str) + " %"}),
        hide_index=True,
        use_container_width=True,
    )

# ------------------------------------------------------------ Stratégie
with onglet_strategie:
    st.header("Stratégie pour la Team Verte")

    st.subheader("1. Nos ressources exclusives à exploiter")
    st.markdown(
        """
        Chaque lieu a **4 ressources globales** (mêmes partout, même prix partout) et **6 ressources
        régionales exclusives** (prix ×1,2 hors de la région). Ce sont ces 6 ressources par lieu qu'il
        faut prioriser pour le commerce : on les récolte moins cher chez nous et on les revend plus cher
        ailleurs.
        """
    )
    ressources_regio = d.ressources_regionales_equipe()
    for lieu_nom, groupe in ressources_regio.groupby("locationName"):
        with st.expander(f"📍 {lieu_nom} — {groupe['activityLabel'].iloc[0]}"):
            st.dataframe(
                groupe[["itemName", "rarity", "minQuantity", "maxQuantity"]].rename(
                    columns={
                        "itemName": "Ressource",
                        "rarity": "Rareté",
                        "minQuantity": "Qté min",
                        "maxQuantity": "Qté max",
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )

    st.subheader("2. Synergies classe + artisanat")
    st.markdown(
        "La synergie donne de l'autonomie économique (pas de bonus de puissance). "
        "À répartir dans l'équipe pour couvrir les 4 artisanats sans doublons inutiles :"
    )
    st.dataframe(d.synergies_classe_artisanat(), hide_index=True, use_container_width=True)

    st.subheader("3. Défense territoriale")
    st.markdown(
        """
        - Une défense (`/territoire`) est **un pari à l'aveugle** sur l'un de nos 4 lieux : elle est
          consommée pour **2 h** dès qu'une tentative valide a lieu, intrus ou non.
        - Sans défense active, un intrus n'est **pas automatiquement détecté**.
        - Intrus découvert : renvoyé à Port Royal, récolte interrompue, et peut subir expulsion,
          confiscation partielle (jamais un Légendaire) ou blocage de récolte 1 h.
        - **Conseil :** tourner les défenses entre lieux selon les heures de forte affluence adverse
          plutôt que de toujours défendre le même lieu.
        """
    )

    st.subheader("4. Commerce")
    st.markdown(
        """
        - Taxe de **2 %** sur chaque vente au Grand Marché (détruite). `/echange` direct = **sans taxe**.
        - Marchand Royal : rachat **×1,10** si ressource en manque au Royaume, **×0,80** en surstock —
          vérifier avant de vendre en masse au marchand plutôt qu'au marché.
        - Ressource **régionale** : ×1,2 à la revente hors de sa région → exporter nos 6 ressources
          exclusives par lieu plutôt que de les vendre sur place.
        """
    )

    st.subheader("5. Repères PvP par classe")
    pvp = d.pvp_classes()
    st.dataframe(
        pvp[["className", "maxHp", "attack", "defense", "critChance", "dodgeChance", "speed"]].rename(
            columns={
                "className": "Classe",
                "maxHp": "PV max",
                "attack": "Attaque",
                "defense": "Défense",
                "critChance": "Chance crit.",
                "dodgeChance": "Esquive",
                "speed": "Vitesse",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

# ------------------------------------------------------------- Profils
with onglet_profils:
    st.header("Profils de l'équipe")
    st.caption("Ajoute, modifie ou supprime des lignes, puis enregistre.")

    options_classe = d.classes()["name"].tolist()
    options_artisanat = d.metiers()[d.metiers()["type"] == "crafting"]["name"].tolist()

    profils = d.charger_profils()
    profils_modifies = st.data_editor(
        profils,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "Classe": st.column_config.SelectboxColumn(options=options_classe),
            "Artisanat": st.column_config.SelectboxColumn(options=options_artisanat),
        },
    )

    if st.button("💾 Enregistrer les profils", type="primary"):
        d.sauvegarder_profils(profils_modifies)
        st.success(f"{len(profils_modifies)} profil(s) enregistré(s).")
