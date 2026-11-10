import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  Sparkles, 
  Download, 
  Copy, 
  Check, 
  FileText, 
  Cpu, 
  Paperclip, 
  Trash2, 
  ChevronRight,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { apiFetch, getApiBaseUrl } from '../apiClient';

export default function AgentsWorkspaceView({ selectedAgentId, onSelectAgent }) {
  const { language, t, isRtl } = useLanguage();
  const [agents, setAgents] = useState([]);
  const [currentAgentId, setCurrentAgentId] = useState(selectedAgentId || "agent_grant_writer");
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [exportingDoc, setExportingDoc] = useState(false);
  const [exportMessage, setExportMessage] = useState("");
  const messagesEndRef = useRef(null);

  // Helper functions for localized titles & roles
  const getAgentTitle = (ag) => {
    if (!ag) return "";
    if (ag.id === "agent_grant_writer") return t("agentGrantWriterTitle");
    if (ag.id === "agent_project_manager") return t("agentProjectManagerTitle");
    if (ag.id === "agent_finance_auditor") return t("agentFinanceAuditorTitle");
    if (ag.id === "agent_communications") return t("agentCommunicationsTitle");
    return language === "ar" ? ag.name_ar : (language === "en" ? (ag.name_en || ag.name_fr) : ag.name_fr);
  };

  const getAgentRole = (ag) => {
    if (!ag) return "";
    if (ag.id === "agent_grant_writer") return t("agentGrantWriterRole");
    if (ag.id === "agent_project_manager") return t("agentProjectManagerRole");
    if (ag.id === "agent_finance_auditor") return t("agentFinanceAuditorRole");
    if (ag.id === "agent_communications") return t("agentCommunicationsRole");
    return language === "ar" ? ag.role_ar : (language === "en" ? (ag.role_en || ag.role_fr) : ag.role_fr);
  };

  // Fetch agents metadata from backend
  useEffect(() => {
    apiFetch('/api/agents')
      .then(res => res.json())
      .then(data => {
        setAgents(data);
      })
      .catch(err => console.error("Error fetching agents:", err));
  }, []);

  useEffect(() => {
    if (selectedAgentId) {
      setCurrentAgentId(selectedAgentId);
    }
  }, [selectedAgentId]);

  const currentAgent = agents.find(a => a.id === currentAgentId) || {
    id: currentAgentId,
    name_ar: "خبير مقترحات التمويل والمشاريع",
    name_fr: "Expert Montage de Projets & Bailleurs",
    role_ar: "صياغة عروض المشاريع والمذكرات المفاهيمية ومصفوفات المنطق التنموي",
    role_fr: "Rédaction de Concept Notes et Cadres Logiques",
    model_provider: "gemini",
    model_name: "gemini-2.5-flash",
    temperature: 0.35,
    active_tools: ["generate_logframe", "export_docx_proposal"]
  };

  function getStarterPrompts(agentId, lang) {
    if (lang === "fr") {
      if (agentId === "agent_grant_writer") {
        return [
          "Rédiger une note conceptuelle FEM SGP sur la régénération du cèdre",
          "Construire le cadre logique (Logframe) pour la gestion pastorale Agdal",
          "Définir la situation de référence et indicateurs SMART à Azrou",
          "Calculer la séquestration carbone au Moyen Atlas via l'extension"
        ];
      } else if (agentId === "agent_project_manager") {
        return [
          "Établir la matrice des risques environnementaux du reboisement",
          "Calculer le taux d'atteinte des indicateurs femmes de Timahdite",
          "Rédiger le rapport d'avancement semestriel pour le Conseil Provincial",
          "Planifier le rétro-planning d'aménagement du Sentier Botanique"
        ];
      } else if (agentId === "agent_finance_auditor") {
        return [
          "Auditer la conformité ICE d'une facture de plants de cèdre",
          "Ventiler les dépenses du 3ème trimestre par axe stratégique",
          "Effectuer un contrôle de conformité pour marché > 500 000 MAD",
          "Exporter le grand livre actuel au format Excel"
        ];
      } else {
        return [
          "Rédiger un communiqué de presse pour la Journée Internationale des Forêts",
          "Créer des publications LinkedIn et Facebook sur la coopérative de laine",
          "Documenter une success story humaine sur les hauteurs de Timahdite",
          "Préparer la newsletter trimestrielle bilingue de l'AFMI"
        ];
      }
    } else if (lang === "en") {
      if (agentId === "agent_grant_writer") {
        return [
          "Draft GEF SGP concept note on cedar forest regeneration",
          "Build logical framework (Logframe) for Agdal pastoral management",
          "Define baseline and SMART impact indicators for Azrou water basin",
          "Calculate Middle Atlas carbon sequestration via AI plugin"
        ];
      } else if (agentId === "agent_project_manager") {
        return [
          "Prepare environmental risk mitigation matrix for reforestation",
          "Compute KPI achievement rate for Timahdite women cooperative",
          "Draft semi-annual progress report for Provincial Council",
          "Build operational Gantt timeline for Botanical Trail"
        ];
      } else if (agentId === "agent_finance_auditor") {
        return [
          "Audit vendor invoice compliance with Moroccan ICE & VAT",
          "Distribute Q3 disbursements across AFMI strategic axes",
          "Run precautionary audit on tender exceeding 500,000 MAD",
          "Export current general ledger to Excel format"
        ];
      } else {
        return [
          "Draft press release for International Day of Forests",
          "Create LinkedIn and Facebook posts for natural wool cooperative",
          "Document human impact story from high Middle Atlas Timahdite",
          "Prepare bilingual quarterly newsletter for AFMI members"
        ];
      }
    } else { // Arabic
      if (agentId === "agent_grant_writer") {
        return [
          "صياغة مذكرة مشروع لبرنامج GEF SGP حول تجدد غابة الأرز",
          "إعداد مصفوفة الإطار المنطقي (Logframe) لمشروع التدبير الرعوي أكدال",
          "تحديد خط الأساس والمؤشرات الذكية (SMART) لمشروع مياه أزرو",
          "حساب تخزين الكربون بالأطلس المتوسط بواسطة الإضافة البرمجية"
        ];
      } else if (agentId === "agent_project_manager") {
        return [
          "إعداد جدول تقييم المخاطر البيئية لمشروع التشجير",
          "حساب معدل إنجاز مؤشرات مشروع تمكين نساء تماحضيت",
          "صياغة تقرير تقدم الأنشطة السداسي للمجلس الإقليمي",
          "وضع خطة العمل الزمنية لتهيئة Sentier Botanique"
        ];
      } else if (agentId === "agent_finance_auditor") {
        return [
          "تدقيق مطابقة فاتورة شراء شتلات الأرز مع معايير ICE",
          "توزيع نفقات الربع الثالث حسب المحاور الإستراتيجية",
          "إجراء تدقيق احترازي لطلب عروض يفوق 500,000 درهم",
          "تصدير Grand Livre الحالي إلى ملف Excel"
        ];
      } else {
        return [
          "صياغة بلاغ صحفي بمناسبة اليوم العالمي للغابات",
          "كتابة منشور لينكد إن وفيسبوك حول تعاونيات الصوف الطبيعي",
          "توثيق قصة نجاح إنسانية من أعالي جبال تماحضيت",
          "إعداد النشرة الإخبارية الفصلية للجمعية ثنائية اللغة"
        ];
      }
    }
  }

  // Pre-populate welcoming starter messages based on current agent and language
  useEffect(() => {
    let welcome = "";
    if (language === "fr") {
      if (currentAgentId === "agent_grant_writer") {
        welcome = "Bonjour. Je suis l'Expert Bailleurs & Projets de l'AFMI. Je vous assiste dans le montage de Concept Notes, matrices de cadre logique et l'alignement avec les exigences des bailleurs (FEM SGP, ANEF, INDH, GIZ, UE). Comment puis-je vous aider aujourd'hui ?";
      } else if (currentAgentId === "agent_project_manager") {
        welcome = "Bonjour. Je suis le Chef de Projet et Spécialiste M&E. J'assure le suivi des indicateurs terrain au Moyen Atlas, la gestion des risques et la rédaction des rapports d'avancement périodiques.";
      } else if (currentAgentId === "agent_finance_auditor") {
        welcome = "Bienvenue dans l'unité d'audit financier. J'analyse vos relevés bancaires, vérifie la conformité des factures (ICE/TVA) et ventile les dépenses selon les axes stratégiques de l'AFMI.";
      } else if (currentAgentId === "agent_communications") {
        welcome = "Bonjour. Je suis le Chargé de Communication et Médias de l'AFMI. Je vous aide à rédiger vos communiqués de presse, articles de valorisation et publications pour les réseaux sociaux.";
      }
    } else if (language === "en") {
      if (currentAgentId === "agent_grant_writer") {
        welcome = "Welcome. I am AFMI's Grant Proposal & Donor Expert. I can assist you with Concept Notes, Logical Framework matrices (Logframes), and proposal alignment with international donors (GEF SGP, ANEF, INDH, GIZ, EU). How can I support your project today?";
      } else if (currentAgentId === "agent_project_manager") {
        welcome = "Hello. I am the Project Manager & M&E Specialist. I monitor field indicators across the Middle Atlas (cedar saplings planted, protected rangelands, cooperative beneficiaries), risk management, and periodic progress reporting.";
      } else if (currentAgentId === "agent_finance_auditor") {
        welcome = "Welcome to the Financial Audit unit. I parse bank statements, audit vendor invoices, validate Moroccan tax IDs (ICE/VAT), and categorize expenses across AFMI's strategic priorities.";
      } else if (currentAgentId === "agent_communications") {
        welcome = "Hello. I am the Institutional Communications & Media Officer for AFMI. I help you draft trilingual press releases, social media posts, and document field success stories in rural Ifrane.";
      }
    } else {
      if (currentAgentId === "agent_grant_writer") {
        welcome = "مرحباً بكم. أنا خبير مقترحات التمويل لجمعية الغابة النموذجية إفران (AFMI). أستطيع مساعدتكم في صياغة مذكرات التمويل (Concept Notes)، مصفوفات الإطار المنطقي (Logframes)، وملاءمة مقترحاتكم مع معايير المانحين (GEF SGP, ANEF, INDH, GIZ, UE). كيف يمكنني دعمكم اليوم؟";
      } else if (currentAgentId === "agent_project_manager") {
        welcome = "أهلاً بكم. أنا مدير المشاريع والمتابعة والتقييم (M&E). أتابع مؤشرات الإنجاز الميدانية بالأطلس المتوسط (أشجار الأرز المغروسة، الأراضي المحمية، المستفيدات بتماحضيت)، وتدبير المخاطر البيئية وإعداد تقارير الإنجاز الدورية.";
      } else if (currentAgentId === "agent_finance_auditor") {
        welcome = "مرحباً بكم في وحدة التدقيق المالي. أقوم بمراجعة كشوفات الحسابات البنكية (Relevés bancaires)، مطابقة الفواتير، التحقق من أرقام التعريف الجبائي (ICE / TVA)، وتصنيف النفقات حسب المحاور الإستراتيجية الستة لـ AFMI.";
      } else if (currentAgentId === "agent_communications") {
        welcome = "مرحباً بكم. أنا مسؤول التواصل والإعلام المؤسساتي لـ AFMI. أساعدكم في صياغة البلاغات الصحفية ثنائية اللغة (عربي / فرنسي)، كتابة منشورات منصات التواصل الاجتماعي، وتوثيق قصص النجاح الميدانية بالمناطق القروية لإفران.";
      }
    }
    
    setMessages([
      {
        sender: "assistant",
        text: welcome,
        time: new Date().toLocaleTimeString(language === 'ar' ? 'ar-MA' : 'fr-FR', { hour: '2-digit', minute: '2-digit' }),
        suggested_actions: getStarterPrompts(currentAgentId, language)
      }
    ]);
  }, [currentAgentId, language]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSendMessage = async (textToSend) => {
    const query = textToSend || inputMessage;
    if (!query.trim() || isLoading) return;

    const userMsg = {
      sender: "user",
      text: query,
      time: new Date().toLocaleTimeString(language === 'ar' ? 'ar-MA' : 'fr-FR', { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputMessage("");
    setIsLoading(true);

    try {
      const res = await apiFetch(`/api/agents/${currentAgentId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: query,
          language: language
        })
      });

      if (!res.ok) throw new Error("Erreur de réponse serveur");
      const data = await res.json();

      const assistantMsg = {
        sender: "assistant",
        text: data.response,
        time: new Date().toLocaleTimeString(language === 'ar' ? 'ar-MA' : 'fr-FR', { hour: '2-digit', minute: '2-digit' }),
        suggested_actions: data.suggested_actions || []
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      console.error(err);
      const errMsg = language === 'fr' 
        ? "Désolé, une erreur est survenue lors du traitement. Veuillez vérifier le serveur local ou la connexion réseau."
        : (language === 'en' 
          ? "Sorry, an error occurred while processing your request. Please ensure the local server is running or check your connection."
          : "عذراً، حدث خطأ أثناء معالجة الطلب. يرجى التأكد من تشغيل الخادم المحلي أو الاتصال بالإنترنت.");

      setMessages(prev => [
        ...prev,
        {
          sender: "assistant",
          text: errMsg,
          time: new Date().toLocaleTimeString(language === 'ar' ? 'ar-MA' : 'fr-FR', { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleExportDocx = async (content) => {
    setExportingDoc(true);
    setExportMessage("");
    try {
      const docTitle = language === 'fr' 
        ? `Document Officiel - ${getAgentTitle(currentAgent)}`
        : (language === 'en' 
          ? `Official Document - ${getAgentTitle(currentAgent)}`
          : `وثيقة رسمية - ${getAgentTitle(currentAgent)}`);

      const res = await apiFetch('/api/agents/export-doc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: docTitle,
          content: content,
          agent_id: currentAgentId
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        setExportMessage(language === 'fr' 
          ? `Document généré avec succès : ${data.filename}` 
          : (language === 'en' 
            ? `Document generated successfully: ${data.filename}` 
            : `تم إنشاء المستند بنجاح: ${data.filename}`));
        // Trigger download
        window.open(`${getApiBaseUrl()}/exports/${data.filename}`, '_blank');
      }
    } catch (err) {
      setExportMessage(language === 'fr' ? "Échec de l'exportation." : (language === 'en' ? "Failed to export document." : "تعذر تصدير الملف."));
    } finally {
      setExportingDoc(false);
      setTimeout(() => setExportMessage(""), 4000);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-6.5rem)] bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      
      {/* Agent Selector Top Bar */}
      <div className="bg-slate-50/80 border-b border-slate-200 p-3 flex flex-wrap items-center justify-between gap-3">
        
        {/* Agent Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
          {agents.map((ag) => (
            <button
              key={ag.id}
              onClick={() => setCurrentAgentId(ag.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
                currentAgentId === ag.id
                  ? 'bg-afmi-forest text-white shadow-sm'
                  : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
              }`}
            >
              <span>{ag.id === 'agent_grant_writer' ? '📑' : ag.id === 'agent_project_manager' ? '🌲' : ag.id === 'agent_finance_auditor' ? '🔍' : '📢'}</span>
              <span>{getAgentTitle(ag)}</span>
            </button>
          ))}
        </div>

        {/* Current Agent Meta info */}
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <div className="flex items-center gap-1.5 bg-white px-2.5 py-1 rounded-lg border border-slate-200">
            <Cpu className="w-3.5 h-3.5 text-afmi-forest" />
            <span className="font-mono text-[11px] font-semibold">{currentAgent.model_provider}:{currentAgent.model_name}</span>
          </div>
          <button 
            onClick={() => setMessages([])}
            className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
            title={t('clearChat')}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>

      </div>

      {/* Agent Header Profile Card */}
      <div className="px-6 py-3 bg-slate-50/40 border-b border-slate-100 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-slate-800 text-sm">{getAgentTitle(currentAgent)}</h3>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{getAgentRole(currentAgent)}</p>
        </div>
        <div className="flex items-center gap-1.5">
          {currentAgent.active_tools?.map((tool, i) => (
            <span key={i} className="text-[10px] bg-afmi-lightmint text-afmi-forest font-semibold px-2 py-0.5 rounded-md border border-afmi-mint/30">
              🛠️ {tool}
            </span>
          ))}
        </div>
      </div>

      {/* Messages Transcript */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-5 bg-slate-50/20">
        
        {messages.map((msg, idx) => {
          const isUser = msg.sender === "user";
          return (
            <div key={idx} className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
              
              {/* Avatar */}
              <div className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center text-sm shadow-xs ${
                isUser ? 'bg-afmi-gold text-white font-bold' : 'bg-afmi-forest text-white'
              }`}>
                {isUser ? (language === 'ar' ? 'أنا' : 'Me') : '🌲'}
              </div>

              {/* Message Bubble */}
              <div className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-4 text-sm leading-relaxed ${
                isUser
                  ? 'bg-afmi-forest text-white shadow-sm rounded-tr-none'
                  : 'bg-white text-slate-800 border border-slate-200/80 shadow-xs rounded-tl-none'
              }`}>
                
                {/* Bubble Header */}
                <div className="flex items-center justify-between gap-4 mb-2 pb-1.5 border-b border-slate-100 text-[11px]">
                  <span className={`font-bold ${isUser ? 'text-emerald-100' : 'text-afmi-forest'}`}>
                    {isUser ? t('userSenderTitle') : getAgentTitle(currentAgent)}
                  </span>
                  <span className={`text-[10px] ${isUser ? 'text-emerald-200' : 'text-slate-400'}`}>
                    {msg.time}
                  </span>
                </div>

                {/* Content */}
                <div className="whitespace-pre-wrap font-sans text-[13.5px] leading-relaxed">
                  {msg.text}
                </div>

                {/* Action Buttons for Assistant response */}
                {!isUser && (
                  <div className="mt-4 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                    
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => handleCopy(msg.text, idx)}
                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500 hover:text-afmi-forest px-2 py-1 rounded hover:bg-slate-50 transition-colors"
                      >
                        {copiedIndex === idx ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedIndex === idx ? t('copied') : t('copyText')}</span>
                      </button>

                      <button
                        onClick={() => handleExportDocx(msg.text)}
                        disabled={exportingDoc}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-afmi-forest hover:bg-afmi-lightmint px-2.5 py-1 rounded-md transition-colors border border-afmi-mint/40"
                      >
                        <FileText className="w-3 h-3 text-afmi-forest" />
                        <span>{t('exportDocx')}</span>
                      </button>
                    </div>

                    {exportMessage && (
                      <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                        {exportMessage}
                      </span>
                    )}
                  </div>
                )}

                {/* Suggested Action Pills */}
                {!isUser && msg.suggested_actions && msg.suggested_actions.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-100">
                    <span className="text-[11px] font-bold text-slate-400 block mb-1.5">
                      {t('suggestedActions')}
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.suggested_actions.map((action, aIdx) => (
                        <button
                          key={aIdx}
                          onClick={() => handleSendMessage(action)}
                          className="text-[11px] bg-slate-50 hover:bg-afmi-lightmint hover:text-afmi-forest text-slate-700 px-2.5 py-1 rounded-lg border border-slate-200 transition-colors flex items-center gap-1 font-medium text-start"
                        >
                          <span>{action}</span>
                          <ArrowRight className={`w-3 h-3 text-slate-400 shrink-0 ${isRtl ? 'transform rotate-180' : ''}`} />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            </div>
          );
        })}

        {/* Loading Bubble */}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-xl bg-afmi-forest text-white flex items-center justify-center text-sm shadow-xs animate-pulse">
              🌲
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none p-4 text-xs text-slate-500 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-afmi-gold animate-spin" />
              <span>{t('loadingAi')}</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box & Action Controls */}
      <div className="p-3 md:p-4 bg-white border-t border-slate-200">
        <form 
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={`${t('inputPlaceholder')} ${getAgentTitle(currentAgent)}...`}
            className="flex-1 bg-slate-50 border border-slate-200 focus:border-afmi-forest focus:ring-1 focus:ring-afmi-forest rounded-xl px-4 py-3 text-sm text-slate-800 placeholder-slate-400 outline-none transition-all"
            disabled={isLoading}
          />
          
          <button
            type="submit"
            disabled={!inputMessage.trim() || isLoading}
            className="bg-afmi-forest hover:bg-afmi-emerald text-white font-bold p-3 rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm shadow-afmi-forest/20 shrink-0 flex items-center justify-center"
          >
            <Send className={`w-4 h-4 ${isRtl ? 'transform rotate-180' : ''}`} />
          </button>
        </form>

        <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2 px-1">
          <span>{t('inputFooterNote')}</span>
          <span className="font-mono">AFMI AI Core v1.0</span>
        </div>
      </div>

    </div>
  );
}
