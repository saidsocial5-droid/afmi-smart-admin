import React from 'react';
import { 
  TrendingUp, 
  Wallet, 
  FileCheck, 
  Coins, 
  ArrowUpRight, 
  Bot, 
  Trees, 
  ShieldCheck, 
  Calendar,
  AlertCircle,
  FileSpreadsheet,
  FileText
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function DashboardView({ 
  projects = [], 
  grants = [], 
  transactions = [], 
  financeSummary = {}, 
  onSelectAgent,
  onNavigateTab
}) {
  const { t, language } = useLanguage();
  const totalBudget = projects.reduce((acc, p) => acc + (p.total_budget || 0), 0);
  const totalSpent = projects.reduce((acc, p) => acc + (p.spent_budget || 0), 0);
  const totalGrantsRequested = grants.reduce((acc, g) => acc + (g.amount_requested || 0), 0);
  const currentBalance = financeSummary.current_balance || 264000.0;

  const agentsList = [
    {
      id: "agent_grant_writer",
      title: t('agentGrantWriterTitle'),
      role: t('agentGrantWriterRole'),
      icon: "📑",
      badge: "GEF / ANEF / UE",
      color: "from-emerald-700 to-afmi-forest"
    },
    {
      id: "agent_project_manager",
      title: t('agentProjectManagerTitle'),
      role: t('agentProjectManagerRole'),
      icon: "🌲",
      badge: "KPIs & M&E",
      color: "from-teal-800 to-emerald-900"
    },
    {
      id: "agent_finance_auditor",
      title: t('agentFinanceAuditorTitle'),
      role: t('agentFinanceAuditorRole'),
      icon: "🔍",
      badge: "Relevés & Factures",
      color: "from-amber-700 to-afmi-forest"
    },
    {
      id: "agent_communications",
      title: t('agentCommunicationsTitle'),
      role: t('agentCommunicationsRole'),
      icon: "📢",
      badge: language === 'ar' ? "عربية / فرنسية / إنجليزية" : "Trilingue AR/FR/EN",
      color: "from-slate-800 to-afmi-forest"
    }
  ];

  return (
    <div className="space-y-6">
      
      {/* Institutional Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-afmi-gradient text-white p-6 md:p-8 shadow-lg shadow-afmi-forest/15">
        <div className="absolute left-0 bottom-0 opacity-10 pointer-events-none transform translate-y-8 -translate-x-8">
          <span className="text-[180px]">🌲</span>
        </div>
        
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-md px-3 py-1 rounded-full text-xs font-semibold text-afmi-lightmint mb-3 border border-white/20">
            <span>{t('heroRegion')}</span>
            <span className="opacity-60">•</span>
            <span>{t('heroProvince')}</span>
          </div>
          
          <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight mb-2">
            {t('heroTitle')}
          </h2>
          <p className="text-sm md:text-base text-emerald-100 leading-relaxed font-normal">
            {t('heroDesc')}
          </p>

          <div className="flex flex-wrap items-center gap-3 mt-5">
            <button
              onClick={() => onNavigateTab('agents')}
              className="inline-flex items-center gap-2 bg-white text-afmi-forest px-4 py-2.5 rounded-xl font-bold text-sm shadow hover:bg-emerald-50 transition-colors"
            >
              <Bot className="w-4 h-4 text-afmi-forest" />
              <span>{t('heroBtnAgents')}</span>
            </button>
            <button
              onClick={() => onNavigateTab('ocr')}
              className="inline-flex items-center gap-2 bg-white/15 backdrop-blur-md border border-white/25 text-white px-4 py-2.5 rounded-xl font-semibold text-sm hover:bg-white/25 transition-colors"
            >
              <FileCheck className="w-4 h-4 text-afmi-gold" />
              <span>{t('heroBtnOcr')}</span>
            </button>
            <button
              onClick={() => onNavigateTab('radar')}
              className="inline-flex items-center gap-2 bg-amber-500/30 backdrop-blur-md border border-amber-300/40 text-amber-100 px-4 py-2.5 rounded-xl font-semibold text-sm hover:bg-amber-500/40 transition-colors"
            >
              <span className="text-sm">📡</span>
              <span>{t('heroBtnRadar')}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Top 4 Financial & Project Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Total Projects Budget */}
        <div className="afmi-card p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{t('statActivePortfolio')}</span>
            <div className="p-2 bg-emerald-50 text-emerald-700 rounded-lg">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-afmi-dark">
            {totalBudget.toLocaleString()} <span className="text-xs font-semibold text-slate-400">{t('currencyMAD')}</span>
          </div>
          <p className="text-xs text-slate-500 mt-2 flex items-center gap-1 font-medium">
            <span className="text-emerald-600 font-bold">{projects.length}</span> {t('statActiveProjectsCount')}
          </p>
        </div>

        {/* Consumed / Spent Budget */}
        <div className="afmi-card p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{t('statSpentBudget')}</span>
            <div className="p-2 bg-blue-50 text-blue-700 rounded-lg">
              <Coins className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-afmi-dark">
            {totalSpent.toLocaleString()} <span className="text-xs font-semibold text-slate-400">{t('currencyMAD')}</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-3 overflow-hidden">
            <div 
              className="bg-blue-600 h-1.5 rounded-full" 
              style={{ width: `${Math.min(100, (totalSpent / (totalBudget || 1)) * 100)}%` }}
            ></div>
          </div>
          <p className="text-xs text-slate-500 mt-2 font-medium">
            {t('statBurnRate')}: <span className="font-bold text-blue-600">{Math.round((totalSpent / (totalBudget || 1)) * 100)}%</span>
          </p>
        </div>

        {/* Available Bank Balance */}
        <div className="afmi-card p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{t('statBankBalance')}</span>
            <div className="p-2 bg-amber-50 text-amber-700 rounded-lg">
              <Wallet className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-afmi-dark">
            {currentBalance.toLocaleString()} <span className="text-xs font-semibold text-slate-400">{t('currencyMAD')}</span>
          </div>
          <p className="text-xs text-slate-500 mt-2 font-medium">
            {t('statBankBranch')}
          </p>
        </div>

        {/* Grants Pipeline */}
        <div className="afmi-card p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{t('statGrantsRequested')}</span>
            <div className="p-2 bg-purple-50 text-purple-700 rounded-lg">
              <FileCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-afmi-dark">
            {totalGrantsRequested.toLocaleString()} <span className="text-xs font-semibold text-slate-400">{t('currencyMAD')}</span>
          </div>
          <p className="text-xs text-slate-500 mt-2 font-medium">
            <span className="text-purple-600 font-bold">{grants.length}</span> {t('statGrantsCount')}
          </p>
        </div>

      </div>

      {/* 4 Specialized AI Agents Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-afmi-dark">{t('agentsSectionTitle')}</h3>
            <p className="text-xs text-slate-500">{t('agentsSectionSubtitle')}</p>
          </div>
          <button 
            onClick={() => onNavigateTab('agents')}
            className="text-xs font-bold text-afmi-forest hover:text-emerald-700 flex items-center gap-1"
          >
            <span>{t('openAgentsWorkspace')}</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {agentsList.map((agent) => (
            <div 
              key={agent.id}
              onClick={() => onSelectAgent(agent.id)}
              className="afmi-card p-5 afmi-card-hover cursor-pointer border-t-4 border-t-afmi-forest flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-2xl p-2 bg-slate-50 rounded-xl border border-slate-100">{agent.icon}</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                    {agent.badge}
                  </span>
                </div>
                <h4 className="font-bold text-afmi-dark text-base">{agent.title}</h4>
                <p className="text-xs text-slate-600 leading-relaxed mt-2">{agent.role}</p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-afmi-forest font-bold">
                <span>{t('startImmediateWork')}</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Middle Atlas Projects & Financial Ledger Snapshot */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Active Projects Tracker */}
        <div className="lg:col-span-2 afmi-card p-5">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
            <div>
              <h3 className="font-bold text-afmi-dark text-base">{t('activeProjectsTitle')}</h3>
              <p className="text-xs text-slate-400">{t('activeProjectsSubtitle')}</p>
            </div>
            <button 
              onClick={() => onNavigateTab('grants')}
              className="text-xs font-bold text-afmi-forest hover:underline"
            >
              {t('viewAll')}
            </button>
          </div>

          <div className="space-y-4">
            {projects.map((proj) => {
              const burnRate = Math.round((proj.spent_budget / (proj.total_budget || 1)) * 100);
              return (
                <div key={proj.id} className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/60 hover:bg-slate-50 transition-colors">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-afmi-lightmint text-afmi-forest">
                          {proj.code}
                        </span>
                        <span className="text-xs font-semibold text-slate-500">
                          {proj.donor}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-800 leading-snug">{proj.title}</h4>
                    </div>
                    <span className="text-xs font-bold text-afmi-forest shrink-0">
                      {proj.total_budget.toLocaleString()} {proj.currency || t('currencyMAD')}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-500 mb-1.5">
                    <span>{t('location')}: {proj.location}</span>
                    <span>{t('burnRateLabel')}: {burnRate}%</span>
                  </div>

                  <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
                    <div 
                      className="bg-afmi-forest h-1.5 rounded-full" 
                      style={{ width: `${Math.min(100, burnRate)}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent Transactions & OCR Audit Snapshot */}
        <div className="afmi-card p-5">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
            <div>
              <h3 className="font-bold text-afmi-dark text-base">{t('recentAuditedTitle')}</h3>
              <p className="text-xs text-slate-400">{t('recentAuditedSubtitle')}</p>
            </div>
            <button 
              onClick={() => onNavigateTab('ocr')}
              className="text-xs font-bold text-afmi-forest hover:underline"
            >
              {t('labBtn')}
            </button>
          </div>

          <div className="space-y-3">
            {transactions.slice(0, 4).map((tx) => (
              <div key={tx.id} className="p-3 rounded-lg border border-slate-100 bg-white shadow-2xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-semibold text-slate-400 font-mono">{tx.tx_date}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                    tx.credit > 0 
                      ? 'bg-emerald-50 text-emerald-700' 
                      : 'bg-rose-50 text-rose-700'
                  }`}>
                    {tx.credit > 0 ? `+${tx.credit.toLocaleString()} ${t('currencyMAD')}` : `-${tx.debit.toLocaleString()} ${t('currencyMAD')}`}
                  </span>
                </div>
                <p className="text-xs font-semibold text-slate-700 line-clamp-1">{tx.label}</p>
                <div className="flex items-center justify-between mt-2 text-[10px] text-slate-400">
                  <span className="truncate max-w-[150px]">{tx.beneficiary_or_emitter || 'AFMI'}</span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                    {tx.status}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <button 
            onClick={() => onNavigateTab('ocr')}
            className="w-full mt-4 py-2 px-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-bold text-afmi-forest hover:bg-slate-100 flex items-center justify-center gap-1.5"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>{t('viewFullLedger')}</span>
          </button>
        </div>

      </div>

    </div>
  );
}
