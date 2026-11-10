"""
AFMI Carbon Calculator Plugin
Specialized for Middle Atlas Forest Ecosystems (Cedrus atlantica, Quercus rotundifolia)
"""

def calculate_forest_carbon_offset(surface_ha: float, tree_species: str = "Cedrus atlantica", duration_years: int = 20) -> dict:
    """
    Calculates estimated carbon sequestration (tCO2e) for forestry projects in the Ifrane/Middle Atlas region.
    Based on Moroccan National Forestry Research (INRF) allometric tables.
    """
    # Sequestration factors in tons CO2 equivalent / ha / year
    factors = {
        "Cedrus atlantica": 6.8,       # Cèdre de l'Atlas
        "Quercus rotundifolia": 3.4,   # Chêne vert
        "Pinus halepensis": 4.5,       # Pin d'Alep
        "Mixed Native": 5.2            # Écosystème mixte Moyen Atlas
    }
    rate = factors.get(tree_species, 5.0)
    total_co2 = surface_ha * rate * duration_years
    
    # Valuation at voluntary carbon credit standard (approx 120 MAD / tCO2)
    economic_value_mad = total_co2 * 120.0

    return {
        "surface_hectares": surface_ha,
        "species": tree_species,
        "duration_years": duration_years,
        "sequestration_rate_per_ha_yr": rate,
        "total_tco2e_sequestered": round(total_co2, 2),
        "estimated_carbon_credit_value_mad": round(economic_value_mad, 2),
        "certification_standard": "Plan Vivo / Gold Standard Forestry Adaptation Morocco"
    }

def register_plugin(registry):
    """Entry point called by AgentRegistry upon startup."""
    # Register tool to Grant Writer and Project Manager
    grant_writer = registry.get_agent("agent_grant_writer")
    if grant_writer:
        grant_writer.register_tool(
            "calculate_forest_carbon_offset",
            calculate_forest_carbon_offset,
            "Calculer le potentiel de séquestration carbone (tCO2e) et valeur des crédits pour la cédraie du Moyen Atlas."
        )

    pm = registry.get_agent("agent_project_manager")
    if pm:
        pm.register_tool(
            "calculate_forest_carbon_offset",
            calculate_forest_carbon_offset,
            "Calculer les bénéfices carbone et indicateurs climatiques des reboisements AFMI."
        )
