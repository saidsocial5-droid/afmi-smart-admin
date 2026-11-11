import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.exc import SQLAlchemyError
from backend.core.database import SessionLocal, AgentConfigModel, ProjectModel, GrantPipelineModel
from backend.core.llm_router import llm_router
from backend.config.settings import settings

class BaseAgent(ABC):
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.ngo_profile = self._load_ngo_profile()
        self.load_config()

    def _load_ngo_profile(self) -> Dict[str, Any]:
        try:
            with open(settings.ngo_profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[BaseAgent] Error loading ngo_profile: {e}")
            return {}

    def load_config(self):
        """Fetch dynamic configuration from SQLite database."""
        db = SessionLocal()
        try:
            try:
                cfg = db.query(AgentConfigModel).filter(AgentConfigModel.id == self.agent_id).first()
            except SQLAlchemyError:
                # Fresh install: agents are instantiated at import time, before init_db() creates the tables.
                # Defaults are used until the next load_config() call (every get_agent()).
                cfg = None
            if cfg:
                self.name_ar = cfg.name_ar
                self.name_fr = cfg.name_fr
                self.role_ar = cfg.role_ar
                self.role_fr = cfg.role_fr
                self.description = cfg.description
                self.system_prompt = cfg.system_prompt
                self.temperature = cfg.temperature
                self.model_provider = cfg.model_provider
                self.model_name = cfg.model_name
                self.custom_instructions = cfg.custom_instructions or ""
                self.active_tools = json.loads(cfg.active_tools) if cfg.active_tools else []
                self.is_active = cfg.is_active
            else:
                self.name_ar = "وكيل ذكي"
                self.name_fr = "Agent Intelligent"
                self.role_ar = "مساعد مؤسساتي"
                self.role_fr = "Assistant Institutionnel"
                self.description = ""
                self.system_prompt = "Tu es un assistant IA pour l'AFMI."
                self.temperature = 0.4
                self.model_provider = settings.default_provider
                self.model_name = settings.gemini_model
                self.custom_instructions = ""
                self.active_tools = []
                self.is_active = True
        finally:
            db.close()

    def register_tool(self, name: str, func: Callable, description: str, parameters: Optional[Dict[str, Any]] = None):
        """Register a dynamic tool/skill into the agent."""
        self.tools[name] = {
            "function": func,
            "description": description,
            "parameters": parameters or {}
        }

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Outil non trouvé: {tool_name}")
        func = self.tools[tool_name]["function"]
        # Handle async or sync functions
        if callable(func):
            import inspect
            if inspect.iscoroutinefunction(func):
                return await func(**kwargs)
            return func(**kwargs)
        raise ValueError(f"L'outil {tool_name} n'est pas exécutable.")

    def get_rag_context(self) -> str:
        """Inject shared institutional memory and active portfolio context."""
        # Re-read so edits from the Institutional Memory view apply on the next request without restart
        self.ngo_profile = self._load_ngo_profile()
        db = SessionLocal()
        context_parts = []
        try:
            # 1. Institutional Base Info
            org = self.ngo_profile.get("organization", {})
            axes = self.ngo_profile.get("strategic_axes", [])
            donors = self.ngo_profile.get("target_donors", [])
            partners = self.ngo_profile.get("partners", [])
            
            context_parts.append(f"""### 🏛️ Identité Institutionnelle de l'AFMI :
- Nom : {org.get('name_fr')} ({org.get('name_ar')})
- Siège : {org.get('headquarters')}
- Statut : {org.get('legal_status')}
- Identifiants légaux : ICE {org.get('ice')} | IF {org.get('identifiant_fiscal')} | RIB {org.get('rib_banque')} ({org.get('banque_nom')})
- Mission : {self.ngo_profile.get('mission')}

### 🎯 Axes Stratégiques Prioritaires :
{chr(10).join(f"- {axis}" for axis in axes)}

### 🤝 Bailleurs & Partenaires Ciblés :
- Bailleurs : {", ".join(donors)}
- Partenaires : {", ".join(partners)}""")

            # 2. Dynamic DB Context (Active Projects)
            projects = db.query(ProjectModel).limit(5).all()
            if projects:
                context_parts.append("\n### 📂 Projets en cours dans le portefeuille AFMI :")
                for p in projects:
                    context_parts.append(f"- [{p.code}] {p.title} | Bailleur : {p.donor} | Budget : {p.total_budget:,.2f} {p.currency} | Statut : {p.status}")

            # 2 bis. Mémoire documentaire (Lot 6) : documents de référence de la GED (conventions, rapports finaux, évaluations)
            context_parts.extend(self._key_documents_context())

            # 3. Dynamic Grants Pipeline
            grants = db.query(GrantPipelineModel).limit(5).all()
            if grants:
                context_parts.append("\n### 📑 Opportunités de subvention en cours de montage :")
                for g in grants:
                    context_parts.append(f"- {g.title} | Bailleur : {g.donor} | Montant demandé : {g.amount_requested:,.2f} {g.currency} | Échéance : {g.deadline} | Statut : {g.status}")

        finally:
            db.close()

        return "\n\n".join(context_parts)

    @staticmethod
    def _key_documents_context() -> list:
        """Résumés des documents de référence de la base unique (absents si la base n'est pas disponible)."""
        from backend.core import unified_db
        try:
            with unified_db.connect() as conn:
                rows = conn.execute(
                    "SELECT d.Title, d.DocType, d.ExtractedSummary, p.Code FROM Documents d JOIN Projects p ON p.Id = d.ProjectId "
                    "WHERE d.IsDeleted = 0 AND (d.IsKeyReference = 1 OR d.DocType IN ('Convention', 'Rapport final', 'Rapport d''évaluation')) "
                    "ORDER BY COALESCE(d.SignatureDate, d.UploadedDate) DESC LIMIT 6").fetchall()
        except Exception:
            return []
        if not rows:
            return []
        lines = ["\n### 📚 Documents de référence (GED des projets) :"]
        lines += [f"- [{r['Code']}] {r['DocType'] or 'Document'} « {r['Title']} » : {(r['ExtractedSummary'] or '')[:280]}" for r in rows]
        return lines

    def assemble_system_prompt(self, language: str = "ar") -> str:
        """Combine dynamic prompt, institutional profile, and custom instructions."""
        self.load_config()
        rag_context = self.get_rag_context()
        
        # Language directive
        if language == "fr":
            lang_directive = "### 🌐 DIRECTIVE LINGUISTIQUE OBLIGATOIRE :\nTu DOIS répondre entièrement et exclusivement en FRANÇAIS, en adoptant un style institutionnel, technique, rigoureux et précis adapté aux standards des bailleurs (FEM, UE, ANEF, INDH)."
        elif language == "en":
            lang_directive = "### 🌐 MANDATORY LANGUAGE DIRECTIVE :\nYou MUST respond entirely and professionally in ENGLISH, adopting formal NGO institutional and grant standards applicable to Moroccan conservation and international donors (GEF, EU, World Bank, etc.)."
        else:
            lang_directive = "### 🌐 توجيه لغوي إلزامي :\nيجب أن تكون إجابتك باللغة العربية الفصحى المؤسساتية الرصينة، مع الالتزام بالدقة التقنية والمصطلحات المعتمدة لدى جمعية AFMI والمانحين بالمملكة المغربية."

        full_prompt = f"""{self.system_prompt}

{rag_context}

{lang_directive}

### ⚙️ Directives Spécifiques Personnalisées :
{self.custom_instructions if self.custom_instructions else "Aucune directive additionnelle."}

### 🛠️ Outils Actifs Disponibles :
{", ".join(self.active_tools) if self.active_tools else "Mode analyse conversationnelle pure."}

RÈGLE D'OR : Assure-toi que toutes les réponses reflètent les standards institutionnels de l'AFMI, avec un respect rigoureux de la précision technique et des réalités territoriales du Moyen Atlas (Azrou, Ifrane, Timahdite)."""
        return full_prompt

    async def run(
        self,
        user_message: str,
        context_data: Optional[Dict[str, Any]] = None,
        images_b64: Optional[List[str]] = None,
        language: str = "ar"
    ) -> Dict[str, Any]:
        """Execute agent workflow and return standardized response."""
        full_system_prompt = self.assemble_system_prompt(language=language)
        
        # Call LLM Router
        response_text, engine_used = await llm_router.generate_with_meta(
            prompt=user_message,
            system_prompt=full_system_prompt,
            provider=self.model_provider,
            model_name=self.model_name,
            temperature=self.temperature,
            images_b64=images_b64
        )

        # Generate suggested follow-up actions based on agent role and language
        suggested_actions = self._generate_suggested_actions(user_message, response_text, language=language)

        return {
            "agent_id": self.agent_id,
            "name_ar": self.name_ar,
            "name_fr": self.name_fr,
            "response": response_text,
            "suggested_actions": suggested_actions,
            "model_used": engine_used,
            "generated_documents": []
        }

    def _generate_suggested_actions(self, user_msg: str, response: str, language: str = "ar") -> List[str]:
        """Generate intuitive follow-up prompt pills for the UI in the target language."""
        if language == "fr":
            if self.agent_id == "agent_grant_writer":
                return [
                    "Exporter cette proposition en document Word (.docx) officiel",
                    "Générer la matrice du cadre logique (Logframe Matrix)",
                    "Détailler le budget estimatif en dirhams marocains (MAD)",
                    "Aligner la proposition avec les critères du FEM SGP Maroc"
                ]
            elif self.agent_id == "agent_project_manager":
                return [
                    "Calculer les indicateurs clés de performance (KPIs)",
                    "Élaborer la matrice d'évaluation des risques environnementaux",
                    "Rédiger le rapport semestriel d'avancement des activités",
                    "Générer le planning opérationnel des interventions"
                ]
            elif self.agent_id == "agent_finance_auditor":
                return [
                    "Exporter le grand livre audité au format Excel (.xlsx)",
                    "Vérifier la conformité TVA et mentions obligatoires",
                    "Contrôler la validité de l'identifiant commun ICE",
                    "Ventiler les dépenses par axe stratégique AFMI"
                ]
            elif self.agent_id == "agent_communications":
                return [
                    "Rédiger le communiqué de presse bilingue (Arabe / Français)",
                    "Créer des posts optimisés pour LinkedIn et Facebook",
                    "Raconter une success story humaine de Timahdite",
                    "Ajouter les hashtags médias environnementaux Maroc"
                ]
            return ["Continuer la conversation", "Exporter en document Word (.docx)"]
        elif language == "en":
            if self.agent_id == "agent_grant_writer":
                return [
                    "Export this proposal to official Word (.docx) format",
                    "Generate logical framework matrix (Logframe)",
                    "Detail the estimated budget in Moroccan Dirhams (MAD)",
                    "Align proposal with GEF SGP Morocco standards"
                ]
            elif self.agent_id == "agent_project_manager":
                return [
                    "Calculate Key Performance Indicators (KPIs)",
                    "Draft environmental risk assessment matrix",
                    "Prepare semi-annual field progress report",
                    "Generate project operational workplan"
                ]
            elif self.agent_id == "agent_finance_auditor":
                return [
                    "Export audited transactions to Excel (.xlsx)",
                    "Verify Moroccan VAT and invoice compliance",
                    "Validate Common Business Identifier (ICE)",
                    "Classify expenses by AFMI strategic priorities"
                ]
            elif self.agent_id == "agent_communications":
                return [
                    "Draft press release in Arabic and English",
                    "Create social media posts for LinkedIn and Facebook",
                    "Document community success story from Timahdite",
                    "Add environmental media outreach hashtags"
                ]
            return ["Follow up on this topic", "Export response to Word (.docx)"]
        else: # Arabic
            if self.agent_id == "agent_grant_writer":
                return [
                    "تصدير هذا المقترح إلى ملف Word (.docx) رسمي",
                    "صياغة مصفوفة الإطار المنطقي (Logframe Matrix)",
                    "إعداد الميزانية التقديرية بالدرهم المغربي (MAD)",
                    "ملاءمة المقترح مع معايير GEF SGP Maroc"
                ]
            elif self.agent_id == "agent_project_manager":
                return [
                    "حساب مؤشرات الإنجاز الرئيسية (KPIs)",
                    "إعداد جدول تقييم المخاطر وتدابير التخفيف",
                    "صياغة تقرير تقدم الأنشطة الميدانية",
                    "تصدير مخطط جانت الزمني للمشروع"
                ]
            elif self.agent_id == "agent_finance_auditor":
                return [
                    "تصدير جدول العمليات المدققة إلى Excel (.xlsx)",
                    "مطابقة المبالغ مع معايير الضريبة على القيمة المضافة TVA",
                    "التحقق من صحة رقم التعريف الموحد للمقاولة ICE",
                    "توزيع النفقات حسب المحاور الإستراتيجية"
                ]
            elif self.agent_id == "agent_communications":
                return [
                    "توليد نسخة البلاغ الصحفي باللغة العربية والفرنسية",
                    "إنشاء منشورات مهيأة لمنصة LinkedIn و Facebook",
                    "صياغة قصة نجاح إنسانية من تعاونية تماحضيت",
                    "إضافة وسومات موجهة للإعلام البيئي المغربي"
                ]
            return ["متابعة الاستفسار", "تصدير النتيجة بصيغة Word"]
