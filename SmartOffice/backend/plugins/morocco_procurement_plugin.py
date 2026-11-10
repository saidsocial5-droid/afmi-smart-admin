"""
AFMI Moroccan Public Procurement & Association Compliance Plugin
Checks conformity against Moroccan Law (Décret n° 2-22-431 relatif aux marchés publics & Dahir 1958)
"""

def audit_tender_compliance(
    supplier_ice: str,
    amount_ttc: float,
    has_tax_certificate: bool = True,
    has_cnss_certificate: bool = True,
    has_commercial_register: bool = True
) -> dict:
    """Audit compliance for high-value purchases according to Moroccan public grant rules."""
    issues = []
    
    clean_ice = "".join(filter(str.isdigit, str(supplier_ice)))
    if len(clean_ice) != 15:
        issues.append("ICE invalide ou non conforme (15 chiffres obligatoires).")
        
    # Ceiling for direct purchase orders (Bons de commande) in Morocco is generally 500,000 MAD TTC
    if amount_ttc > 500000.0:
        issues.append("Dépassement du seuil légal des bons de commande (500 000 DH). Nécessite un appel d'offres ouvert.")

    if not has_tax_certificate and amount_ttc > 50000.0:
        issues.append("Attestation de régularité fiscale (DGI) manquante pour achat supérieur à 50 000 DH.")

    if not has_cnss_certificate and amount_ttc > 50000.0:
        issues.append("Attestation d'affiliation à la CNSS manquante.")

    is_compliant = len(issues) == 0

    return {
        "is_compliant": is_compliant,
        "amount_ttc": amount_ttc,
        "supplier_ice": clean_ice,
        "audit_verdict": "DOSSIER CONFORME POUR FINANCEMENT PUBLIC / BAILLEUR" if is_compliant else "NON CONFORME - DOCUMENTS MANQUANTS",
        "identified_issues": issues,
        "recommended_action": "Valider le paiement et archiver les pièces justificatives." if is_compliant else "Suspendre le paiement jusqu'à régularisation du dossier fournisseur."
    }

def register_plugin(registry):
    finance_auditor = registry.get_agent("agent_finance_auditor")
    if finance_auditor:
        finance_auditor.register_tool(
            "audit_tender_compliance",
            audit_tender_compliance,
            "Auditer la conformité d'un achat ou marché selon la réglementation marocaine des marchés publics et subventions."
        )
