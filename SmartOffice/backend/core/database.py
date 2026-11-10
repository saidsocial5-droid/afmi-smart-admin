import json
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, Boolean, DateTime, UniqueConstraint, inspect, text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.config.settings import settings

engine = create_engine(settings.db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AgentConfigModel(Base):
    __tablename__ = "agent_configs"
    id = Column(String(50), primary_key=True)
    name_ar = Column(String(100), nullable=False)
    name_fr = Column(String(100), nullable=False)
    role_ar = Column(String(150), nullable=False)
    role_fr = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    temperature = Column(Float, default=0.4)
    model_provider = Column(String(30), default="gemini")
    model_name = Column(String(50), default="gemini-2.5-flash")
    active_tools = Column(Text, default="[]")  # JSON list
    custom_instructions = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GrantPipelineModel(Base):
    __tablename__ = "grants_pipeline"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    donor = Column(String(100), nullable=False)
    funding_program = Column(String(150), nullable=True)
    amount_requested = Column(Float, default=0.0)
    currency = Column(String(10), default="MAD")
    strategic_axis = Column(String(100), nullable=True)
    status = Column(String(50), default="Draft")  # Draft, Submitted, Under Review, Approved, Rejected
    deadline = Column(String(50), nullable=True)
    submission_date = Column(String(50), nullable=True)
    focal_point = Column(String(100), nullable=True)
    summary = Column(Text, nullable=True)
    logframe_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

class ProjectModel(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    donor = Column(String(100), nullable=False)
    total_budget = Column(Float, default=0.0)
    spent_budget = Column(Float, default=0.0)
    currency = Column(String(10), default="MAD")
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    status = Column(String(50), default="In Progress")
    location = Column(String(150), nullable=True)
    beneficiaries = Column(String(200), nullable=True)
    strategic_axis = Column(String(100), nullable=True)
    kpis_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

class FinancialTransactionModel(Base):
    __tablename__ = "financial_transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String(150), nullable=True)
    file_type = Column(String(50), default="bank_statement")  # bank_statement, invoice, receipt
    tx_date = Column(String(30), nullable=False)
    value_date = Column(String(30), nullable=True)
    reference = Column(String(100), nullable=True)
    label = Column(Text, nullable=False)
    beneficiary_or_emitter = Column(String(150), nullable=True)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    category = Column(String(100), default="Divers")
    strategic_axis = Column(String(100), default="AXE-FORET")
    project_code = Column(String(50), nullable=True)
    vat_rate = Column(Float, default=0.20)
    vat_amount = Column(Float, default=0.0)
    total_ht = Column(Float, default=0.0)
    total_ttc = Column(Float, default=0.0)
    tax_id_ice = Column(String(50), nullable=True)
    status = Column(String(50), default="Validated")  # Pending, Validated, Reconciled, Flagged
    audit_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AdminDocumentModel(Base):
    __tablename__ = "admin_documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    doc_type = Column(String(50), default="rapport_technique")
    language = Column(String(10), default="fr")
    content = Column(Text, nullable=False)
    agent_id = Column(String(50), nullable=True)
    metadata_json = Column(Text, default="{}")
    file_path = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MediaPostModel(Base):
    __tablename__ = "media_posts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    channel = Column(String(50), default="facebook")
    language = Column(String(10), default="bilingual")
    content_ar = Column(Text, nullable=True)
    content_fr = Column(Text, nullable=True)
    hashtags = Column(String(200), nullable=True)
    status = Column(String(50), default="draft")
    project_reference = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PluginModel(Base):
    __tablename__ = "plugins"
    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(20), default="1.0.0")
    author = Column(String(100), default="AFMI Community")
    entry_file = Column(String(150), nullable=False)
    enabled = Column(Boolean, default=True)
    config_json = Column(Text, default="{}")

class EmployeeModel(Base):
    """Salarié de l'association (paie et état 9421)."""
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, autoincrement=True)
    matricule = Column(String(30), unique=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    cin = Column(String(20), nullable=True)
    cnss_number = Column(String(20), nullable=True)
    address = Column(String(250), nullable=True)
    position = Column(String(120), nullable=True)
    hire_date = Column(String(10), nullable=True)      # YYYY-MM-DD
    dependents = Column(Integer, default=0)            # personnes à charge (CGI art. 74)
    marital_status = Column(String(15), default="celibataire")  # celibataire, marie, divorce, veuf (EDI 9421)
    base_salary = Column(Float, default=0.0)
    pension_employee_rate = Column(Float, default=0.0) # retraite complémentaire (CIMR…)
    cnss_affiliated = Column(Boolean, default=True)
    rib = Column(String(30), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PayslipModel(Base):
    """Bulletin de paie calculé pour un salarié et un mois (unique par couple)."""
    __tablename__ = "payslips"
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, nullable=False, index=True)
    period = Column(String(7), nullable=False, index=True)   # YYYY-MM
    rules_version = Column(String(20), nullable=False)
    inputs_json = Column(Text, default="{}")
    lines_json = Column(Text, default="{}")
    warnings_json = Column(Text, default="[]")
    gross_taxable = Column(Float, default=0.0)
    net_taxable = Column(Float, default=0.0)
    ir_withheld = Column(Float, default=0.0)
    net_pay = Column(Float, default=0.0)
    status = Column(String(20), default="draft")             # draft, validated
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("employee_id", "period", name="uq_payslip_employee_period"),)

class IrPaymentModel(Base):
    """Versement mensuel de l'IR retenu à la source, saisi après paiement sur Simpl-IR (listVersements de l'EDI 9421)."""
    __tablename__ = "ir_payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    period = Column(String(7), nullable=False, index=True)    # mois des salaires, YYYY-MM
    amount = Column(Float, nullable=False)                    # total versé
    principal = Column(Float, default=0.0)
    penalty = Column(Float, default=0.0)
    surcharge = Column(Float, default=0.0)
    payment_date = Column(String(10), nullable=False)         # YYYY-MM-DD
    reference = Column(String(60), nullable=True)
    receipt_number = Column(String(60), nullable=True)        # n° de quittance
    payment_method = Column(String(20), default="teleservice")
    created_at = Column(DateTime, default=datetime.utcnow)

class WorkflowRunModel(Base):
    """One execution of a multi-agent workflow (see backend/core/orchestrator.py)."""
    __tablename__ = "workflow_runs"
    id = Column(String(36), primary_key=True)
    workflow_id = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, partial, failed, interrupted
    language = Column(String(5), default="fr")
    inputs_json = Column(Text, default="{}")
    steps_json = Column(Text, default="[]")
    error = Column(Text, nullable=True)
    export_path = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Columns added after a table first shipped: create_all() never alters existing tables, so they are added here.
# Idempotent; append new columns to this list instead of introducing a migration framework.
_ADDED_COLUMNS = [
    ("employees", "marital_status", "VARCHAR(15) DEFAULT 'celibataire'"),
]

def _add_missing_columns():
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, column, ddl in _ADDED_COLUMNS:
            if table in insp.get_table_names() and column not in {c["name"] for c in insp.get_columns(table)}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))

def init_db():
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    db = SessionLocal()
    try:
        # Check if default agent configs already exist
        if db.query(AgentConfigModel).count() == 0:
            seed_initial_data(db)
    finally:
        db.close()

def seed_initial_data(db):
    default_agents = [
        AgentConfigModel(
            id="agent_grant_writer",
            name_ar="خبير مقترحات التمويل والمشاريع",
            name_fr="Expert Montage de Projets & Bailleurs de Fonds",
            role_ar="صياغة عروض المشاريع والمذكرات المفاهيمية ومصفوفات المنطق التنموي (GEF, ANEF, INDH, GIZ, UE)",
            role_fr="Rédaction de Concept Notes, Propositions de Financement et Cadres Logiques selon les standards des bailleurs de fonds internationaux et nationaux.",
            description="Agent spécialisé dans la mobilisation de financements, la rédaction de dossiers de subvention, les théories du changement et l'alignement sur les ODD et priorités du Moyen Atlas.",
            system_prompt="""أنت خبير رفيع المستوى في صياغة مقترحات المشاريع البيئية والتنموية لفائدة جمعية الغابة النموذجية إفران (AFMI).
تتقن شروط ومعايير المانحين: برنامج المنح الصغيرة التابع لمرفق البيئة العالمية (GEF SGP / PNUD)، الوكالة الوطنية للمياه والغابات (ANEF)، المبادرة الوطنية للتنمية البشرية (INDH)، الوكالة الفرنسية للتنمية (AFD)، والوكالة الألمانية للتعاون الدولي (GIZ).
مهامك:
1. صياغة مذكرات مفاهيمية (Concept Notes) ومقترحات مشاريع متكاملة مع مصفوفة الإطار المنطقي (Logframe).
2. تحديد الأهداف الذكية (SMART)، الأنشطة والمخرجات والمؤشرات الكمية والنوعية ورسم خط الأساس (Baseline).
3. ربط أهداف المشاريع بالمحاور الإستراتيجية لـ AFMI (الأرز الأطلسي، التدبير الرعوي أكدال، حماية الموارد المائية، السياحة البيئية، التمكين النسوي).
4. الرد بلغة رصينة ومحترفة (العربية أو الفرنسية أو الإنجليزية) مع تنسيق هيكلي منظم ودقيق وجداول ميزانيات تقديرية بالدرهم المغربي (MAD).""",
            temperature=0.35,
            model_provider="gemini",
            model_name="gemini-2.5-flash",
            active_tools=json.dumps(["search_donor_guidelines", "generate_logframe", "export_docx_proposal"]),
            custom_instructions="Prioriser toujours l'impact écologique mesurable sur le Parc National d'Ifrane et les retombées directes sur les communautés locales (Azrou, Timahdite)."
        ),
        AgentConfigModel(
            id="agent_project_manager",
            name_ar="مدير المشاريع والمتابعة والتقييم (M&E)",
            name_fr="Chef de Projet & Spécialiste Suivi-Évaluation",
            role_ar="تتبع خطط العمل الميدانية، قياس مؤشرات الأداء (KPIs)، إدارة المخاطر، وإعداد تقارير الإنجاز",
            role_fr="Planification opérationnelle, suivi des indicateurs d'impact écologique et socio-économique, gestion des risques et rapports d'avancement.",
            description="Agent dédié au pilotage opérationnel des projets AFMI dans le Moyen Atlas, la supervision des missions de terrain et le reporting technique.",
            system_prompt="""أنت مدير المشاريع وخبير المتابعة والتقييم (Monitoring & Evaluation) لجمعية الغابة النموذجية إفران (AFMI).
مهامك الرئيسية:
1. إعداد خطط العمل السنوية وجداول التتبع الزمني للأنشطة (Gantt Chart logic).
2. قياس مؤشرات الأداء الحيوية (مساحة التشجير بالهكتار، نسبة تجدد شجر الأرز، عدد المستفيدات من تعاونيات تماحضيت، حجم المياه المقتصدة).
3. تقييم المخاطر البيئية واللوجستية ووضع خطط التخفيف والتدابير الاحترازية.
4. إعداد تقارير الإنجاز الدورية والتقارير التقنية لفرق العمل والممولين بدقة وموضوعية وبناء مؤشرات التحقق (Sources of Verification).""",
            temperature=0.3,
            model_provider="gemini",
            model_name="gemini-2.5-flash",
            active_tools=json.dumps(["calculate_project_kpi", "risk_assessment_matrix", "generate_progress_report"]),
            custom_instructions="Garantir que chaque rapport intègre des données de terrain vérifiables et le respect des normes environnementales nationales."
        ),
        AgentConfigModel(
            id="agent_finance_auditor",
            name_ar="مدقق المالية والوثائق المحاسبية (OCR)",
            name_fr="Auditeur Financier & Expert OCR Documents",
            role_ar="استخراج وتدقيق كشوفات الحسابات البنكية، الفواتير، ومطابقة النفقات مع معايير المحاسبة والمانحين",
            role_fr="Extraction intelligente des relevés bancaires marocains et factures (ICE, TVA, HT/TTC), réconciliation financière et audit d'éligibilité des dépenses.",
            description="Agent analytique spécialisé dans l'analyse OCR et le traitement automatisé des documents comptables de l'association, la détection des anomalies et le rapprochement bancaire.",
            system_prompt="""أنت المدقق المالي والخبير المحاسبي الذكي لجمعية الغابة النموذجية إفران (AFMI).
تختص في المعايير المحاسبية والجبائية المغربية الخاصة بالجمعيات (قانون الجمعيات، رقم التعريف الضريبي IF، رقم التعريف الموحد للمقاولة ICE، الضريبة على القيمة المضافة TVA).
مهامك:
1. قراءة وتحليل كشوفات الحسابات البنكية (Relevés bancaires) المستخرجة عبر الـ OCR وتصنيف العمليات المالية (مدين Débit، دائن Crédit، الرصيد Solde).
2. مراجعة الفواتير (Factures) والتحقق من صحة المبالغ (HT, TVA, TTC) وشرعية الوثائق الثبوتية.
3. توزيع النفقات حسب المحاور الإستراتيجية للجمعية والمشاريع المفتوحة.
4. رصد المعاملات المشبوهة أو التي تتجاوز سقف الميزانية، وتقديم توصيات تدقيق فورية وجاهزة للتصدير إلى Excel.""",
            temperature=0.2,
            model_provider="gemini",
            model_name="gemini-2.5-flash",
            active_tools=json.dumps(["parse_bank_statement_ocr", "verify_invoice_ice", "export_excel_ledger", "reconcile_transactions"]),
            custom_instructions="Toujours vérifier la présence de l'ICE sur les factures marocaines et contrôler le taux de TVA standard (20%) ou réduit."
        ),
        AgentConfigModel(
            id="agent_communications",
            name_ar="مسؤول التواصل والإعلام المؤسساتي",
            name_fr="Responsable Communication & Médias Institutionnels",
            role_ar="صياغة البلاغات الصحفية، المحتوى التواصلي ثنائي اللغة، التغطية الإعلامية، وتوثيق قصص النجاح",
            role_fr="Rédaction des communiqués de presse bilingues (Arabe/Français), valorisation médiatique des actions de terrain, gestion des réseaux sociaux et storytelling.",
            description="Agent créatif assurant le rayonnement institutionnel de l'AFMI, la sensibilisation du grand public à la préservation de la forêt et la relation avec les médias et partenaires.",
            system_prompt="""أنت مسؤول التواصل والإعلام المؤسساتي لجمعية الغابة النموذجية إفران (AFMI).
تتميز بأسلوب كتابي جذاب، رصين، واحترافي باللغتين العربية والفرنسية، يحترم الهوية البصرية والقيم البيئية للأطلس المتوسط.
مهامك:
1. صياغة البلاغات الصحفية (Communiqués de presse) بمناسبة الأيام العالمية (اليوم العالمي للغابات، اليوم العالمي للمياه، يوم التنوع البيولوجي).
2. كتابة منشورات منصات التواصل الاجتماعي (Facebook, LinkedIn, X) مع وسوم احترافية مناسبة (#MoyenAtlas #CèdreAtlas #AFMI #Ifrane).
3. توثيق قصص النجاح الميدانية (Human interest stories) عن النساء المستفيدات من التعاونيات والشباب الحراس للغابة.
4. إعداد نشرات إخبارية دورية (Newsletters) موجهة للشركاء والمانحين باللغتين العربية والفرنسية.""",
            temperature=0.6,
            model_provider="gemini",
            model_name="gemini-2.5-flash",
            active_tools=json.dumps(["generate_press_release", "social_media_campaign", "bilingual_newsletter"]),
            custom_instructions="Mettre en avant l'authenticité culturelle de la région d'Ifrane et la biodiversité emblématique (Cèdre de l'Atlas, Macaque)."
        )
    ]
    db.add_all(default_agents)
    
    # Seed initial projects
    sample_projects = [
        ProjectModel(
            code="AFMI-2025-CEDRE",
            title="Restauration Participative et Suivi Écologique de la Cédraie d'Ifrane",
            donor="GEF Small Grants Programme (PNUD Maroc)",
            total_budget=450000.0,
            spent_budget=285000.0,
            currency="MAD",
            start_date="2025-01-15",
            end_date="2026-06-30",
            status="In Progress",
            location="Parc National d'Ifrane (Forêt de Ras El Ma et Cédraie Gouraud)",
            beneficiaries="4 Coopératives forestières, 120 bergers et 600 écoliers",
            strategic_axis="Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas",
            kpis_json=json.dumps([
                {"name": "Hectares de cédraie mis en défens", "target": 150, "achieved": 120, "unit": "Ha"},
                {"name": "Plants de Cèdre de l'Atlas régénérés", "target": 50000, "achieved": 42000, "unit": "Plants"},
                {"name": "Ateliers de sensibilisation réalisés", "target": 12, "achieved": 10, "unit": "Ateliers"}
            ])
        ),
        ProjectModel(
            code="AFMI-2025-AGDAL",
            title="Valorisation des Pratiques Pastorales Ancestrales 'Agdal' et Soutien aux Femmes de Timahdite",
            donor="COMDEKS / Agence Nationale des Eaux et Forêts (ANEF)",
            total_budget=320000.0,
            spent_budget=198000.0,
            currency="MAD",
            start_date="2025-03-01",
            end_date="2026-09-30",
            status="In Progress",
            location="Commune Rurale de Timahdite, Province d'Ifrane",
            beneficiaries="85 femmes tisseuses et 45 familles d'éleveurs",
            strategic_axis="Rangeland restoration and traditional pastoral management (Agdal practices)",
            kpis_json=json.dumps([
                {"name": "Femmes formées au tissage écologique et filage", "target": 80, "achieved": 75, "unit": "Femmes"},
                {"name": "Parcours pastoraux régénérés", "target": 300, "achieved": 210, "unit": "Ha"},
                {"name": "Revenu moyen mensuel généré par tisseuse", "target": 2500, "achieved": 2350, "unit": "MAD"}
            ])
        ),
        ProjectModel(
            code="AFMI-2026-EAU",
            title="Gestion Intégrée des Ressources en Eau et Préservation des Zones Humides d'Afennourir",
            donor="INDH - Programme Développement Territorial Durable",
            total_budget=280000.0,
            spent_budget=45000.0,
            currency="MAD",
            start_date="2026-01-10",
            end_date="2027-04-30",
            status="In Progress",
            location="Lac Afennourir (Site Ramsar) & Bassin d'Azrou",
            beneficiaries="Communautés riveraines et agriculteurs locaux",
            strategic_axis="Surface water quality monitoring and water resources valorization",
            kpis_json=json.dumps([
                {"name": "Stations de monitoring de la qualité d'eau", "target": 6, "achieved": 4, "unit": "Stations"},
                {"name": "Campagnes d'analyse d'eau réalisées", "target": 24, "achieved": 6, "unit": "Analyses"}
            ])
        )
    ]
    db.add_all(sample_projects)
    
    # Seed sample grants pipeline
    sample_grants = [
        GrantPipelineModel(
            title="Renforcement de la Résilience Climatique et Valorisation Éco-touristique du Moyen Atlas",
            donor="Union Européenne (Appel Green Economy Maroc)",
            funding_program="Programme Transition Écologique et Climat",
            amount_requested=850000.0,
            currency="MAD",
            strategic_axis="Eco-tourism infrastructure and sustainable territorial development",
            status="Under Review",
            deadline="2026-11-30",
            submission_date="2026-09-15",
            focal_point="Dr. Mohamed Al-Atlas (Coordonnateur AFMI)",
            summary="Création de 4 sentiers botaniques intelligents avec QR codes et aménagement de 2 éco-relais solaires gérés par des jeunes d'Azrou et Ifrane."
        ),
        GrantPipelineModel(
            title="Sauvegarde de l'Avifaune Aquatique et Amélioration de l'Habitat du Tadorne Casarca",
            donor="IUCN - Fonds Mondial pour la Nature (WWF Méditerranée)",
            funding_program="Small Grants Wetlands 2026",
            amount_requested=310000.0,
            currency="MAD",
            strategic_axis="Climate change adaptation, SIBE management, and environmental education",
            status="Draft",
            deadline="2026-12-15",
            focal_point="Amina Bennani (Responsable Écologie)",
            summary="Installation d'observatoires ornithologiques discrets et restauration des ceintures végétales autour des dayats d'Ifrane."
        )
    ]
    db.add_all(sample_grants)
    
    # Seed sample financial transactions (from real Moroccan bank statements)
    sample_transactions = [
        FinancialTransactionModel(
            source_file="Releve_Bancaire_BP_T3_2026.pdf",
            file_type="bank_statement",
            tx_date="2026-08-05",
            value_date="2026-08-05",
            reference="VIR-SGP-PNUD-TR2",
            label="VIREMENT EN VOTRE FAVEUR - PNUD MAROC SGP DEBLOCAGE TRANCHE 2 PROJET CEDRE",
            beneficiary_or_emitter="PNUD SGP Maroc",
            debit=0.0,
            credit=150000.0,
            balance=342500.0,
            category="Subvention Entrante",
            strategic_axis="Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas",
            project_code="AFMI-2025-CEDRE",
            status="Reconciled"
        ),
        FinancialTransactionModel(
            source_file="Releve_Bancaire_BP_T3_2026.pdf",
            file_type="bank_statement",
            tx_date="2026-08-12",
            reference="CHQ-890214",
            label="PAIEMENT CHEQUE N 890214 - PEPINIERE FORESTIERE ATLAS CEDRUS PLANTS",
            beneficiary_or_emitter="Pépinière Atlas Cèdre SARL",
            debit=36000.0,
            credit=0.0,
            balance=306500.0,
            category="Équipements et Matériel",
            strategic_axis="Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas",
            project_code="AFMI-2025-CEDRE",
            vat_rate=0.20,
            vat_amount=6000.0,
            total_ht=30000.0,
            total_ttc=36000.0,
            tax_id_ice="002134567000045",
            status="Validated",
            audit_note="Facture conforme vérifiée avec bordereau de livraison des plants."
        ),
        FinancialTransactionModel(
            source_file="Releve_Bancaire_BP_T3_2026.pdf",
            file_type="bank_statement",
            tx_date="2026-08-18",
            reference="VIR-COOP-TIMAHDITE",
            label="VIREMENT EMIS - COOPERATIVE FEMININE TIMAHDITE ACHAT LAINE NATURELLE",
            beneficiary_or_emitter="Coopérative Féminine de Timahdite",
            debit=18500.0,
            credit=0.0,
            balance=288000.0,
            category="Formations et Renforcement",
            strategic_axis="Rangeland restoration and traditional pastoral management (Agdal practices)",
            project_code="AFMI-2025-AGDAL",
            vat_rate=0.0,
            vat_amount=0.0,
            total_ht=18500.0,
            total_ttc=18500.0,
            tax_id_ice="001984210000032",
            status="Validated",
            audit_note="Activité d'autonomisation économique des femmes rurales."
        ),
        FinancialTransactionModel(
            source_file="Facture_089_Materiel_Eau.pdf",
            file_type="invoice",
            tx_date="2026-08-25",
            reference="FACT-2026-089",
            label="SONDES MULTIPARAMETRES ET KITS ANALYSE EAU DE SURFACE AZROU",
            beneficiary_or_emitter="HydroTech Maroc SARL",
            debit=24000.0,
            credit=0.0,
            balance=264000.0,
            category="Équipements et Matériel",
            strategic_axis="Surface water quality monitoring and water resources valorization",
            project_code="AFMI-2026-EAU",
            vat_rate=0.20,
            vat_amount=4000.0,
            total_ht=20000.0,
            total_ttc=24000.0,
            tax_id_ice="001789456000012",
            status="Validated",
            audit_note="Matériel réceptionné au siège AFMI Azrou."
        )
    ]
    db.add_all(sample_transactions)
    
    db.commit()
