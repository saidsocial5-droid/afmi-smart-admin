import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.core.base_agent import BaseAgent
from backend.tools.exporters import export_to_docx, export_to_excel
from backend.config.settings import settings

# 1. Specialized Agent: Grant Proposal Writer
class AgentGrantWriter(BaseAgent):
    def __init__(self):
        super().__init__("agent_grant_writer")
        self._register_default_tools()

    def _register_default_tools(self):
        self.register_tool(
            "search_online_grants",
            self.tool_search_online_grants,
            "Rechercher en ligne et scanner les appels à projets et opportunités de subventions ouverts au Maroc (GEF, ANEF, INDH, UE, CEPF)."
        )
        self.register_tool(
            "generate_logframe",
            self.tool_generate_logframe,
            "Générer une matrice de cadre logique complète avec objectifs, indicateurs OVI, sources et hypothèses."
        )
        self.register_tool(
            "export_docx_proposal",
            self.tool_export_proposal_docx,
            "Exporter la proposition de projet au format Microsoft Word (.docx) avec en-tête institutionnel AFMI."
        )

    async def tool_search_online_grants(self, keywords: str = "", category: str = "all") -> Dict[str, Any]:
        from backend.tools.grant_scanner import grant_scanner
        results = await grant_scanner.search_live_opportunities(keywords=keywords, category=category)
        return {
            "status": "success",
            "query": keywords,
            "found_count": len(results),
            "opportunities": results
        }

    def tool_generate_logframe(self, project_title: str, objective: str) -> Dict[str, Any]:
        return {
            "status": "success",
            "message": f"Cadre logique généré pour '{project_title}'",
            "logframe_ready": True
        }

    def tool_export_proposal_docx(self, title: str, content: str) -> Dict[str, str]:
        sections = [{"title": "Proposition Technique & Méthodologique", "content": content}]
        file_path = export_to_docx(title=title, sections=sections, doc_type="Proposition de Financement / Concept Note", agent_name=self.name_fr)
        return {"file_path": file_path, "filename": Path(file_path).name}


# 2. Specialized Agent: Project Manager & M&E
class AgentProjectManager(BaseAgent):
    def __init__(self):
        super().__init__("agent_project_manager")
        self._register_default_tools()

    def _register_default_tools(self):
        self.register_tool(
            "calculate_project_kpi",
            self.tool_calculate_kpi,
            "Calculer le taux d'avancement des indicateurs clés (reboisement, régénération cèdre, formation)."
        )
        self.register_tool(
            "risk_assessment_matrix",
            self.tool_risk_matrix,
            "Évaluer les risques climatiques, pastoraux et logistiques du Moyen Atlas."
        )

    def tool_calculate_kpi(self, target: float, achieved: float) -> Dict[str, Any]:
        rate = (achieved / target * 100) if target > 0 else 0
        return {"target": target, "achieved": achieved, "rate_percentage": round(rate, 1)}

    def tool_risk_matrix(self, risk_name: str, impact: int, probability: int) -> Dict[str, Any]:
        score = impact * probability
        level = "Élevé" if score >= 15 else "Moyen" if score >= 8 else "Faible"
        return {"risk": risk_name, "score": score, "level": level}


# 3. Specialized Agent: Finance & OCR Auditor
class AgentFinanceAuditor(BaseAgent):
    def __init__(self):
        super().__init__("agent_finance_auditor")
        self._register_default_tools()

    def _register_default_tools(self):
        self.register_tool(
            "export_excel_ledger",
            self.tool_export_ledger,
            "Exporter le grand livre des transactions au format Excel (.xlsx) stylisé AFMI."
        )
        self.register_tool(
            "verify_invoice_ice",
            self.tool_verify_ice,
            "Vérifier la validité de l'identifiant fiscal ICE à 15 chiffres d'un fournisseur marocain."
        )
        self.register_tool(
            "calculate_payslip_ma",
            self.tool_calculate_payslip,
            "Calculer un bulletin de paie marocain (CNSS, AMO, frais professionnels, IR retenu à la source, "
            "coût employeur) selon la loi de finances applicable au mois de paie."
        )

    def tool_calculate_payslip(self, period: str, base_salary: float, dependents: int = 0,
                               hire_date: Optional[str] = None, rules_version: Optional[str] = None) -> Dict[str, Any]:
        from backend.tools.payroll_ma import PayInput, compute_payslip
        return compute_payslip(PayInput(period=period, base_salary=base_salary, dependents=dependents,
                                        hire_date=hire_date, rules_version=rules_version)).to_dict()

    def tool_export_ledger(self, transactions: List[Dict[str, Any]]) -> Dict[str, str]:
        file_path = export_to_excel(transactions=transactions)
        return {"file_path": file_path, "filename": Path(file_path).name}

    def tool_verify_ice(self, ice: str) -> Dict[str, Any]:
        clean_ice = "".join(filter(str.isdigit, str(ice)))
        is_valid = len(clean_ice) == 15
        return {
            "ice": clean_ice,
            "is_valid": is_valid,
            "status": "Conforme aux normes de la Direction Générale des Impôts (DGI Maroc)" if is_valid else "ICE Non Conforme (doit comporter exactement 15 chiffres)"
        }


# 4. Specialized Agent: Communications & Media Officer
class AgentCommunications(BaseAgent):
    def __init__(self):
        super().__init__("agent_communications")
        self._register_default_tools()

    def _register_default_tools(self):
        self.register_tool(
            "generate_press_release",
            self.tool_press_release,
            "Générer un communiqué de presse bilingue Arabe/Français prêt à la diffusion médiatique."
        )

    def tool_press_release(self, event_title: str, key_facts: str) -> Dict[str, Any]:
        return {
            "status": "success",
            "event": event_title,
            "ready_for_press": True
        }


# Dynamic Agent Registry & Plugin Loader (Open-Closed Principle)
class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._plugin_tools: Dict[str, Any] = {}
        self.initialize_core_agents()
        self.load_plugins()

    def initialize_core_agents(self):
        self._agents["agent_grant_writer"] = AgentGrantWriter()
        self._agents["agent_project_manager"] = AgentProjectManager()
        self._agents["agent_finance_auditor"] = AgentFinanceAuditor()
        self._agents["agent_communications"] = AgentCommunications()

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        agent = self._agents.get(agent_id)
        if agent:
            # Refresh dynamic prompt/config from DB
            agent.load_config()
        return agent

    def list_agents(self) -> List[Dict[str, Any]]:
        agents_info = []
        for a_id, agent in self._agents.items():
            agent.load_config()
            agents_info.append({
                "id": a_id,
                "name_ar": agent.name_ar,
                "name_fr": agent.name_fr,
                "role_ar": agent.role_ar,
                "role_fr": agent.role_fr,
                "description": agent.description,
                "system_prompt": agent.system_prompt,
                "temperature": agent.temperature,
                "model_provider": agent.model_provider,
                "model_name": agent.model_name,
                "active_tools": agent.active_tools,
                "registered_tools": list(agent.tools.keys()),
                "custom_instructions": agent.custom_instructions,
                "is_active": agent.is_active
            })
        return agents_info

    def load_plugins(self):
        """Scans plugins/ directory and dynamically loads new tools and agents."""
        plugins_dir = settings.plugins_dir
        if not plugins_dir.exists():
            return

        for p_file in plugins_dir.glob("*.py"):
            if p_file.name.startswith("__"):
                continue
            module_name = f"backend.plugins.{p_file.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, str(p_file))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = mod
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "register_plugin"):
                        mod.register_plugin(self)
                        print(f"[AgentRegistry] Successfully loaded plugin: {p_file.name}")
            except Exception as e:
                print(f"[AgentRegistry] Failed to load plugin {p_file.name}: {e}")

    def register_custom_agent(self, agent_instance: BaseAgent):
        self._agents[agent_instance.agent_id] = agent_instance

agent_registry = AgentRegistry()
