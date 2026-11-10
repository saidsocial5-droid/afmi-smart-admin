import React, { useState, useEffect } from 'react';
import { 
  FileScan, 
  Upload, 
  FileSpreadsheet, 
  CheckCircle, 
  AlertCircle, 
  FileText, 
  Save, 
  Trash2, 
  Plus, 
  Download, 
  ShieldCheck, 
  Coins, 
  RefreshCw, 
  ExternalLink,
  Tag
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { apiFetch, getApiBaseUrl } from '../apiClient';

export default function OcrFinanceLabView({ onTransactionsUpdated }) {
  const { language, t, isRtl } = useLanguage();
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentDocName, setCurrentDocName] = useState("");
  const [extractedMetadata, setExtractedMetadata] = useState(null);
  const [extractedTransactions, setExtractedTransactions] = useState([]);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedAxisFilter, setSelectedAxisFilter] = useState("all");

  const [strategicAxes, setStrategicAxes] = useState([
    "السياحة الإيكولوجية والبنية التحتية المستدامة",
    "تقوية القدرات والتمكين المؤسساتي والمحلي",
    "التربية البيئية والمواطنة الإيكولوجية وتوعية الناشئة",
    "الطاقات المتجددة والنجاعة الطاقية والتكنولوجيات النظيفة",
    "التنمية المستدامة والاقتصاد الدائري والمقاولات الخضراء",
    "حماية النظم الإيكولوجية الغابوية ورصد التنوع البيولوجي",
    "استعادة المراعي والتدبير الرعوي التقليدي نظام أكدال",
    "مراقبة جودة المياه السطحية وتثمين الموارد المائية"
  ]);

  useEffect(() => {
    apiFetch('/api/settings/ngo-profile')
      .then(r => r.json())
      .then(data => {
        if (data.strategic_axes && data.strategic_axes.length > 0) {
          setStrategicAxes(data.strategic_axes);
        }
      })
      .catch(err => console.error(err));
  }, []);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    uploadAndParseFile(file);
  };

  const uploadAndParseFile = async (file) => {
    setIsProcessing(true);
    setCurrentDocName(file.name);
    setErrorMessage("");
    setSaveSuccessMsg("");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", "auto");

    try {
      const res = await apiFetch("/api/ocr/upload-and-parse", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Erreur de traitement du document.");
      }

      const data = await res.json();
      setExtractedMetadata(data);
      setExtractedTransactions(data.transactions || []);
    } catch (err) {
      console.error(err);
      setErrorMessage(err.message || (language === 'ar' ? "فشل تحليل الوثيقة. الرجاء المحاولة مجدداً." : "Erreur de traitement du document OCR."));
    } finally {
      setIsProcessing(false);
    }
  };

  const loadSampleDocument = (type) => {
    setIsProcessing(true);
    setErrorMessage("");
    setSaveSuccessMsg("");
    
    // Simulate instantaneous intelligent OCR payload for demonstration
    setTimeout(() => {
      if (type === "bank_statement") {
        setCurrentDocName("Releve_Bancaire_BP_Août_2026.pdf");
        setExtractedMetadata({
          document_type: "releve_bancaire",
          bank_name: "Banque Populaire (Agence Azrou)",
          account_rib: "022 330 0001234567890123 45",
          currency: "MAD",
          extraction_method: "Digital PDF Parser (High-Precision Table & Regex)",
          initial_balance: 192500.0,
          final_balance: 264000.0
        });
        setExtractedTransactions([
          {
            date: "2026-08-05",
            reference: "VIR-PNUD-TR2",
            description: "VIREMENT EN VOTRE FAVEUR PNUD MAROC SGP DEBLOCAGE TRANCHE 2 PROJET CEDRE",
            beneficiary: "PNUD SGP Maroc",
            debit: 0.0,
            credit: 150000.0,
            balance: 342500.0,
            category: "Subvention Entrante",
            strategic_axis: "Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas",
            status: "Validated"
          },
          {
            date: "2026-08-12",
            reference: "CHQ-890214",
            description: "PAIEMENT CHEQUE PEPINIERE ATLAS CEDRUS PLANTS ARBRES AZROU",
            beneficiary: "Pépinière Atlas Cèdre SARL",
            debit: 36000.0,
            credit: 0.0,
            balance: 306500.0,
            category: "Équipements et Matériel",
            strategic_axis: "Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas",
            status: "Validated"
          },
          {
            date: "2026-08-18",
            reference: "VIR-COOP-TIMAHDITE",
            description: "VIREMENT COOPERATIVE FEMININE TIMAHDITE MATIERE PREMIERE LAINE",
            beneficiary: "Coopérative Féminine de Timahdite",
            debit: 18500.0,
            credit: 0.0,
            balance: 288000.0,
            category: "Formations et Renforcement",
            strategic_axis: "Rangeland restoration and traditional pastoral management (Agdal practices)",
            status: "Validated"
          },
          {
            date: "2026-08-25",
            reference: "FACT-2026-089",
            description: "HYDROTECH MAROC SONDES MULTIPARAMETRES CONTROLE EAU TIZGUIT",
            beneficiary: "HydroTech Maroc SARL",
            debit: 24000.0,
            credit: 0.0,
            balance: 264000.0,
            category: "Équipements et Matériel",
            strategic_axis: "Surface water quality monitoring and water resources valorization",
            status: "Validated"
          }
        ]);
      } else {
        setCurrentDocName("Facture_Fournisseur_HydroTech_089.pdf");
        setExtractedMetadata({
          document_type: "facture",
          invoice_number: "FACT-2026-089",
          supplier_name: "HydroTech Maroc SARL",
          ice: "001789456000012",
          if: "34902158",
          total_ht: 20000.0,
          vat_rate: 0.20,
          vat_amount: 4000.0,
          total_ttc: 24000.0,
          currency: "MAD",
          extraction_method: "Multimodal Vision AI (Gemini/Ollama OCR Engine)"
        });
        setExtractedTransactions([
          {
            date: "2026-08-25",
            reference: "FACT-2026-089",
            description: "Achat de 2 sondes de prélèvement d'eau & kits réactifs étalonnage",
            beneficiary: "HydroTech Maroc SARL (ICE: 001789456000012)",
            debit: 24000.0,
            credit: 0.0,
            balance: 0.0,
            category: "Équipements et Matériel",
            strategic_axis: "Surface water quality monitoring and water resources valorization",
            status: "Validated"
          }
        ]);
      }
      setIsProcessing(false);
    }, 600);
  };

  const handleUpdateRow = (idx, field, value) => {
    const updated = [...extractedTransactions];
    updated[idx][field] = value;
    setExtractedTransactions(updated);
  };

  const handleDeleteRow = (idx) => {
    const updated = extractedTransactions.filter((_, i) => i !== idx);
    setExtractedTransactions(updated);
  };

  const handleAddRow = () => {
    const newTx = {
      date: new Date().toISOString().split("T")[0],
      reference: `MAN-${extractedTransactions.length + 1}`,
      description: language === 'ar' ? "عملية محاسبية يدوية جديدة" : "Nouvelle écriture comptable manuelle",
      beneficiary: language === 'ar' ? "مستفيد جديد" : "Nouveau bénéficiaire",
      debit: 0.0,
      credit: 0.0,
      balance: 0.0,
      category: "Divers",
      strategic_axis: strategicAxes[0],
      status: "Validated"
    };
    setExtractedTransactions([...extractedTransactions, newTx]);
  };

  const handleSaveToDatabase = async () => {
    if (extractedTransactions.length === 0) return;
    try {
      const res = await apiFetch("/api/ocr/batch-save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_file: currentDocName || "Document_OCR.pdf",
          file_type: extractedMetadata?.document_type || "bank_statement",
          transactions: extractedTransactions
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        setSaveSuccessMsg(language === 'fr' 
          ? `${data.saved_count} écritures enregistrées avec succès en base de données.` 
          : (language === 'en' 
            ? `${data.saved_count} transactions saved successfully to database.` 
            : `تم حفظ ${data.saved_count} عملية بنجاح في قاعدة البيانات.`));
        if (onTransactionsUpdated) onTransactionsUpdated();
        setTimeout(() => setSaveSuccessMsg(""), 5000);
      }
    } catch (err) {
      setErrorMessage(language === 'ar' ? "حدث خطأ أثناء حفظ العمليات في قاعدة البيانات." : "Erreur lors de l'enregistrement des opérations.");
    }
  };

  const handleExportExcel = () => {
    window.open(`${getApiBaseUrl()}/api/finance/export-excel`, "_blank");
  };

  // Calculations
  const totalDebit = extractedTransactions.reduce((acc, t) => acc + (parseFloat(t.debit) || 0), 0);
  const totalCredit = extractedTransactions.reduce((acc, t) => acc + (parseFloat(t.credit) || 0), 0);
  const netDiff = totalCredit - totalDebit;

  const filteredTransactions = selectedAxisFilter === "all" 
    ? extractedTransactions 
    : extractedTransactions.filter(t => t.strategic_axis === selectedAxisFilter);

  return (
    <div className="space-y-6">
      
      {/* Top Header & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-afmi-lightmint text-afmi-forest font-bold">🔍</span>
            <h2 className="text-xl font-extrabold text-afmi-dark">
              {t('ocrTitle')}
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {t('ocrSubtitle')}
          </p>
        </div>

        {/* Quick Sample Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => loadSampleDocument("bank_statement")}
            className="px-3 py-2 bg-slate-50 hover:bg-emerald-50 text-slate-700 hover:text-afmi-forest border border-slate-200 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
          >
            <span>{t('sampleBankStmt')}</span>
          </button>
          <button
            onClick={() => loadSampleDocument("invoice")}
            className="px-3 py-2 bg-slate-50 hover:bg-emerald-50 text-slate-700 hover:text-afmi-forest border border-slate-200 rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
          >
            <span>{t('sampleInvoice')}</span>
          </button>
        </div>
      </div>

      {/* Upload Drag & Drop Area */}
      <div className="bg-white p-6 rounded-2xl border-2 border-dashed border-slate-200 hover:border-afmi-mint/80 transition-colors text-center relative">
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.webp"
          onChange={handleFileUpload}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isProcessing}
        />
        
        <div className="flex flex-col items-center justify-center space-y-2 pointer-events-none">
          <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center text-afmi-forest">
            {isProcessing ? (
              <RefreshCw className="w-6 h-6 animate-spin text-afmi-forest" />
            ) : (
              <Upload className="w-6 h-6" />
            )}
          </div>
          
          <h4 className="text-sm font-bold text-slate-800">
            {isProcessing ? t('dragDropLoading') : t('dragDropText')}
          </h4>
          <p className="text-xs text-slate-400">
            {t('dragDropFormats')}
          </p>
        </div>
      </div>

      {/* Alerts */}
      {errorMessage && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs font-bold text-rose-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {saveSuccessMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-800 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{saveSuccessMsg}</span>
        </div>
      )}

      {/* Metadata & Extraction Source Banner */}
      {extractedMetadata && (
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-slate-400 block text-[10px] font-bold">{t('processedFile')}</span>
              <span className="font-bold text-slate-800">{currentDocName}</span>
            </div>
            <div className="h-6 w-px bg-slate-200"></div>
            <div>
              <span className="text-slate-400 block text-[10px] font-bold">{t('docType')}</span>
              <span className="font-bold text-afmi-forest">
                {extractedMetadata.document_type === 'releve_bancaire' ? t('bankStatement') : t('invoice')}
              </span>
            </div>
            {extractedMetadata.bank_name && (
              <>
                <div className="h-6 w-px bg-slate-200"></div>
                <div>
                  <span className="text-slate-400 block text-[10px] font-bold">{t('bankEntity')}</span>
                  <span className="font-semibold text-slate-700">{extractedMetadata.bank_name}</span>
                </div>
              </>
            )}
            {extractedMetadata.ice && (
              <>
                <div className="h-6 w-px bg-slate-200"></div>
                <div>
                  <span className="text-slate-400 block text-[10px] font-bold">{t('unifiedIce')}</span>
                  <span className="font-mono font-bold text-slate-800">{extractedMetadata.ice}</span>
                </div>
              </>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="bg-white border border-slate-200 text-slate-600 px-2.5 py-1 rounded-md text-[11px] font-mono font-medium">
              {extractedMetadata.extraction_method || "Hybrid Pipeline"}
            </span>
          </div>
        </div>
      )}

      {/* Financial Summary KPI Bar */}
      {extractedTransactions.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[10px] font-bold text-slate-400 uppercase">{t('totalCredit')}</span>
            <div className="text-lg font-black text-emerald-600 mt-0.5">
              +{totalCredit.toLocaleString()} <span className="text-xs font-semibold">{t('currencyMAD')}</span>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[10px] font-bold text-slate-400 uppercase">{t('totalDebit')}</span>
            <div className="text-lg font-black text-rose-600 mt-0.5">
              -{totalDebit.toLocaleString()} <span className="text-xs font-semibold">{t('currencyMAD')}</span>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[10px] font-bold text-slate-400 uppercase">{t('netFlow')}</span>
            <div className={`text-lg font-black mt-0.5 ${netDiff >= 0 ? 'text-afmi-forest' : 'text-rose-700'}`}>
              {netDiff.toLocaleString()} <span className="text-xs font-semibold">{t('currencyMAD')}</span>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
            <span className="text-[10px] font-bold text-slate-400 uppercase">{t('extractedTxCount')}</span>
            <div className="text-lg font-black text-slate-700 mt-0.5">
              {extractedTransactions.length}
            </div>
          </div>
        </div>
      )}
      {/* Main Extracted Transactions Table */}
      {extractedTransactions.length > 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          
          {/* Table Header Controls */}
          <div className="p-4 bg-slate-50/70 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <h3 className="font-bold text-slate-800 text-sm">
                {t('tableGrandLivre')}
              </h3>
              
              {/* Strategic Axis Filter */}
              <select
                value={selectedAxisFilter}
                onChange={(e) => setSelectedAxisFilter(e.target.value)}
                className="text-xs bg-white border border-slate-200 rounded-lg px-2.5 py-1 font-semibold text-slate-700 outline-none"
              >
                <option value="all">{t('allAxesFilter')}</option>
                {strategicAxes.map((axis, i) => (
                  <option key={i} value={axis}>{axis.slice(0, 45)}...</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleAddRow}
                className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold transition-colors flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{t('addRow')}</span>
              </button>

              <button
                onClick={handleSaveToDatabase}
                className="px-3.5 py-1.5 rounded-lg bg-afmi-forest hover:bg-afmi-emerald text-white text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{t('saveToDb')} ({extractedTransactions.length})</span>
              </button>

              <button
                onClick={handleExportExcel}
                className="px-3.5 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                <span>{t('exportExcel')}</span>
              </button>
            </div>
          </div>

          {/* Table Grid */}
          <div className="overflow-x-auto">
            <table className="w-full text-start text-xs">
              <thead className="bg-slate-100/80 text-slate-600 font-bold border-b border-slate-200">
                <tr>
                  <th className="p-3 w-12 text-center">{t('colNumber')}</th>
                  <th className="p-3 w-28 text-start">{t('colDate')}</th>
                  <th className="p-3 w-28 text-start">{t('colRef')}</th>
                  <th className="p-3 text-start">{t('colLabel')}</th>
                  <th className="p-3 w-40 text-start">{t('colBeneficiary')}</th>
                  <th className="p-3 w-24 text-start">{t('colDebit')}</th>
                  <th className="p-3 w-24 text-start">{t('colCredit')}</th>
                  <th className="p-3 w-44 text-start">{t('colAxis')}</th>
                  <th className="p-3 w-24 text-center">{t('colStatus')}</th>
                  <th className="p-3 w-12 text-center">{t('colDelete')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredTransactions.map((tx, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                    
                    <td className="p-3 text-center font-mono text-slate-400 font-semibold">{idx + 1}</td>
                    
                    {/* Date */}
                    <td className="p-2">
                      <input
                        type="text"
                        value={tx.date || ""}
                        onChange={(e) => handleUpdateRow(idx, "date", e.target.value)}
                        className="w-full font-mono text-xs bg-transparent border-0 focus:ring-1 focus:ring-afmi-forest rounded px-1.5 py-1"
                      />
                    </td>

                    {/* Reference */}
                    <td className="p-2">
                      <input
                        type="text"
                        value={tx.reference || ""}
                        onChange={(e) => handleUpdateRow(idx, "reference", e.target.value)}
                        className="w-full font-mono text-xs bg-transparent border-0 focus:ring-1 focus:ring-afmi-forest rounded px-1.5 py-1"
                      />
                    </td>

                    {/* Description */}
                    <td className="p-2">
                      <input
                        type="text"
                        value={tx.description || ""}
                        onChange={(e) => handleUpdateRow(idx, "description", e.target.value)}
                        className="w-full font-semibold text-xs text-slate-800 bg-transparent border-0 focus:ring-1 focus:ring-afmi-forest rounded px-1.5 py-1"
                      />
                    </td>

                    {/* Beneficiary */}
                    <td className="p-2">
                      <input
                        type="text"
                        value={tx.beneficiary || ""}
                        onChange={(e) => handleUpdateRow(idx, "beneficiary", e.target.value)}
                        className="w-full text-xs text-slate-600 bg-transparent border-0 focus:ring-1 focus:ring-afmi-forest rounded px-1.5 py-1"
                      />
                    </td>

                    {/* Debit */}
                    <td className="p-2 text-start">
                      <input
                        type="number"
                        step="0.01"
                        value={tx.debit || ""}
                        onChange={(e) => handleUpdateRow(idx, "debit", parseFloat(e.target.value) || 0)}
                        placeholder="0.00"
                        className="w-full text-start font-mono font-bold text-xs text-rose-700 bg-transparent border-0 focus:ring-1 focus:ring-afmi-forest rounded px-1.5 py-1"
                      />
                    </td>

                    {/* Credit */}
                    <td className="p-2 text-start">
                      <input
                        type="number"
                        step="0.01"
                        value={tx.credit || ""}
                        onChange={(e) => handleUpdateRow(idx, "credit", parseFloat(e.target.value) || 0)}
                        placeholder="0.00"
                        className="w-full text-start font-mono font-bold text-xs text-emerald-700 bg-transparent border-0 focus:ring-1 focus:ring-afmi-forest rounded px-1.5 py-1"
                      />
                    </td>

                    {/* Strategic Axis */}
                    <td className="p-2">
                      <select
                        value={tx.strategic_axis || strategicAxes[0]}
                        onChange={(e) => handleUpdateRow(idx, "strategic_axis", e.target.value)}
                        className="w-full text-[11px] bg-slate-50 border border-slate-200 rounded px-1.5 py-1 text-slate-700"
                      >
                        {strategicAxes.map((ax, aIdx) => (
                          <option key={aIdx} value={ax}>{ax.slice(0, 35)}...</option>
                        ))}
                      </select>
                    </td>

                    {/* Status */}
                    <td className="p-2 text-center">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {tx.status || 'Validated'}
                      </span>
                    </td>

                    {/* Delete */}
                    <td className="p-2 text-center">
                      <button
                        onClick={() => handleDeleteRow(idx)}
                        className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                        title={t('colDelete')}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>

                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </div>
      ) : (
        <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-3">
          <FileScan className="w-12 h-12 text-slate-300 mx-auto" />
          <h3 className="text-base font-bold text-slate-700">{t('emptyOcrTitle')}</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            {t('emptyOcrDesc')}
          </p>
        </div>
      )}

    </div>
  );
}
