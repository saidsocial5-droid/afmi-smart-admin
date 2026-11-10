import React, { useState, useEffect } from 'react';
import {
  Users, Calculator, FileSpreadsheet, Landmark, Plus, Save, Trash2, Play, CheckCircle2,
  Download, ExternalLink, AlertTriangle, Loader2, FileText, X
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { apiFetch, getApiBaseUrl } from '../apiClient';

const EMPTY_EMPLOYEE = {
  matricule: "", full_name: "", cin: "", cnss_number: "", address: "", position: "",
  hire_date: "", dependents: 0, marital_status: "celibataire", base_salary: 0, pension_employee_rate: 0,
  cnss_affiliated: true, rib: "", active: true
};

const MARITAL_STATUSES = ['celibataire', 'marie', 'divorce', 'veuf'];
const PAYMENT_METHODS = ['teleservice', 'virement', 'cheque', 'especes'];
const EMPLOYER_FIELDS = ['identifiant_fiscal', 'raison_sociale', 'commune_code', 'adresse', 'numero_cnss',
  'numero_rc', 'identifiant_tp', 'numero_telephone', 'email'];

const currentPeriod = () => new Date().toISOString().slice(0, 7);
const fmt = (n) => (Number(n) || 0).toLocaleString('fr-MA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

async function call(path, options = {}) {
  const res = await apiFetch(path, {
    ...options,
    headers: options.body ? { 'Content-Type': 'application/json' } : undefined
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(' ; ') : data.detail;
    throw new Error(detail || res.statusText);
  }
  return data;
}

const openExport = (filename) => window.open(`${getApiBaseUrl()}/exports/${filename}`, '_blank');
const openPortal = (url) => window.open(url, '_blank');

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold text-slate-600">{label}</span>
      {children}
    </label>
  );
}

const inputCls = "mt-1 w-full rounded-lg border border-slate-300 p-2 text-sm focus:border-afmi-forest focus:outline-none";

export default function PayrollView() {
  const { t } = useLanguage();
  const [tab, setTab] = useState('payroll');
  const [employees, setEmployees] = useState([]);
  const [editing, setEditing] = useState(null);
  const [period, setPeriod] = useState(currentPeriod());
  const [payslips, setPayslips] = useState([]);
  const [variables, setVariables] = useState({});
  const [monthly, setMonthly] = useState(null);
  const [year, setYear] = useState(new Date().getFullYear() - 1);
  const [annual, setAnnual] = useState(null);
  const [rules, setRules] = useState(null);
  const [sim, setSim] = useState({ period: currentPeriod(), base_salary: 6000, dependents: 0, hire_date: "", rules_version: "" });
  const [simResult, setSimResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [edi, setEdi] = useState(null);            // { config, employer_effective, schema_file, schemas_dir }
  const [ediCheck, setEdiCheck] = useState(null);  // { errors, warnings, schema_file }
  const [showEdiConfig, setShowEdiConfig] = useState(false);
  const [payments, setPayments] = useState([]);
  const [newPayment, setNewPayment] = useState({ period: "", amount: "", payment_date: "", reference: "", receipt_number: "", payment_method: "teleservice" });

  const notify = (text, isError = false) => setMessage({ text, isError });

  const run = async (fn) => {
    setBusy(true);
    setMessage(null);
    try { await fn(); } catch (e) { notify(e.message, true); } finally { setBusy(false); }
  };

  const loadEmployees = () => call('/api/payroll/employees').then(setEmployees);
  const loadPayslips = () => call(`/api/payroll/payslips?period=${period}`).then(setPayslips);
  const loadMonthly = () => call(`/api/payroll/declarations/monthly/${period}`).then(setMonthly);
  const loadAnnual = async () => {
    const [a, cfg, check, pays] = await Promise.all([
      call(`/api/payroll/declarations/9421/${year}`),
      call('/api/payroll/edi/config'),
      call(`/api/payroll/declarations/9421/${year}/edi/preflight`),
      call(`/api/payroll/ir-payments?year=${year}`)
    ]);
    setAnnual(a);
    setEdi(cfg);
    setEdiCheck(check);
    setPayments(pays);
  };

  const saveEdiConfig = () => run(async () => {
    await call('/api/payroll/edi/config', { method: 'PUT', body: JSON.stringify(edi.config) });
    setShowEdiConfig(false);
    await loadAnnual();
    notify(t('payEdiConfigSaved'));
  });

  const setEdiField = (section, key, value, sub) => {
    const config = structuredClone(edi.config);
    if (sub) config[section][sub][key] = value; else config[section][key] = value;
    setEdi({ ...edi, config });
  };

  const exportEdi = () => run(async () => {
    const res = await call(`/api/payroll/declarations/9421/${year}/edi`, { method: 'POST' });
    openExport(res.filename);
    notify(res.schema_validated ? `${t('payEdiValidated')} (${res.schema_file})` : t('payEdiNotValidated'), !res.schema_validated);
  });

  const addPayment = () => run(async () => {
    await call('/api/payroll/ir-payments', { method: 'POST',
      body: JSON.stringify({ ...newPayment, amount: Number(newPayment.amount) }) });
    setNewPayment({ ...newPayment, period: "", amount: "", reference: "", receipt_number: "" });
    await loadAnnual();
  });

  const deletePayment = (id) => run(async () => {
    await call(`/api/payroll/ir-payments/${id}`, { method: 'DELETE' });
    await loadAnnual();
  });

  useEffect(() => {
    run(async () => {
      await loadEmployees();
      setRules(await call('/api/payroll/rules'));
    });
  }, []);

  useEffect(() => {
    if (/^\d{4}-\d{2}$/.test(period)) run(async () => { await loadPayslips(); await loadMonthly(); });
  }, [period]);

  useEffect(() => {
    if (tab === 'declarations' && year > 2016) run(loadAnnual);
  }, [tab, year]);

  const saveEmployee = () => run(async () => {
    const body = { ...editing, hire_date: editing.hire_date || null,
      dependents: Number(editing.dependents), base_salary: Number(editing.base_salary),
      pension_employee_rate: Number(editing.pension_employee_rate) };
    const path = editing.id ? `/api/payroll/employees/${editing.id}` : '/api/payroll/employees';
    await call(path, { method: editing.id ? 'PUT' : 'POST', body: JSON.stringify(body) });
    setEditing(null);
    await loadEmployees();
    notify(t('payEmployeeSaved'));
  });

  const deleteEmployee = (emp) => {
    if (!window.confirm(`${t('payConfirmDelete')} ${emp.full_name} ?`)) return;
    run(async () => {
      const res = await call(`/api/payroll/employees/${emp.id}`, { method: 'DELETE' });
      await loadEmployees();
      notify(res.message);
    });
  };

  const setVar = (empId, key, value) =>
    setVariables({ ...variables, [empId]: { ...(variables[empId] || {}), [key]: Number(value) || 0 } });

  const computePayroll = () => run(async () => {
    const res = await call(`/api/payroll/runs/${period}`, { method: 'POST', body: JSON.stringify({ variables }) });
    await loadPayslips();
    await loadMonthly();
    notify(`${res.computed} ${t('payComputed')}${res.locked ? ` · ${res.locked} ${t('payLocked')}` : ''}${res.errors.length ? ' · ' + res.errors.join(' ; ') : ''}`, res.errors.length > 0);
  });

  const validatePeriod = () => {
    if (!window.confirm(t('payConfirmValidate'))) return;
    run(async () => {
      await call(`/api/payroll/periods/${period}/validate`, { method: 'POST' });
      await loadPayslips();
      await loadMonthly();
    });
  };

  const exportMonthly = (kind) => run(async () => {
    const res = await call(`/api/payroll/declarations/monthly/${period}/export?kind=${kind}`, { method: 'POST' });
    openExport(res.filename);
  });

  const exportPayslip = (id) => run(async () => {
    const res = await call(`/api/payroll/payslips/${id}/export-docx`, { method: 'POST' });
    openExport(res.filename);
  });

  const export9421 = () => run(async () => {
    const res = await call(`/api/payroll/declarations/9421/${year}/export`, { method: 'POST' });
    openExport(res.filename);
  });

  const simulate = () => run(async () => {
    const body = { ...sim, base_salary: Number(sim.base_salary), dependents: Number(sim.dependents),
      hire_date: sim.hire_date || null, rules_version: sim.rules_version || null };
    setSimResult(await call('/api/payroll/simulate', { method: 'POST', body: JSON.stringify(body) }));
  });

  const tabs = [
    { id: 'payroll', label: t('payTabPayroll'), icon: Calculator },
    { id: 'employees', label: t('payTabEmployees'), icon: Users },
    { id: 'declarations', label: t('payTabDeclarations'), icon: Landmark },
    { id: 'simulator', label: t('payTabSimulator'), icon: FileSpreadsheet },
  ];
  const activeEmployees = employees.filter(e => e.active);
  const allValidated = payslips.length > 0 && payslips.every(p => p.status === 'validated');

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-br from-afmi-forest to-afmi-emerald rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center gap-3">
          <Landmark className="w-8 h-8 text-afmi-gold" />
          <div>
            <h1 className="text-2xl font-bold">{t('payTitle')}</h1>
            <p className="text-emerald-100 text-sm mt-1">{t('paySubtitle')}</p>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold ${tab === id ? 'bg-afmi-forest text-white' : 'bg-white border border-slate-200 text-slate-600 hover:border-afmi-sage'}`}>
            <Icon className="w-4 h-4" /> {label}
          </button>
        ))}
        {busy && <Loader2 className="w-5 h-5 animate-spin text-afmi-forest self-center" />}
      </div>

      {message && (
        <div className={`flex items-start justify-between gap-3 rounded-xl p-3 text-sm ${message.isError ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-800'}`}>
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)}><X className="w-4 h-4" /></button>
        </div>
      )}

      {/* ---------------- Monthly payroll ---------------- */}
      {tab === 'payroll' && (
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <Field label={t('payPeriod')}>
              <input type="month" value={period} onChange={e => setPeriod(e.target.value)} className={inputCls} />
            </Field>
            <button onClick={computePayroll} disabled={busy || activeEmployees.length === 0}
              className="flex items-center gap-2 bg-afmi-forest hover:bg-afmi-emerald disabled:opacity-50 text-white font-bold px-4 py-2 rounded-xl">
              <Play className="w-4 h-4" /> {t('payCompute')}
            </button>
            <button onClick={validatePeriod} disabled={busy || payslips.length === 0 || allValidated}
              className="flex items-center gap-2 border border-afmi-forest text-afmi-forest disabled:opacity-40 font-bold px-4 py-2 rounded-xl">
              <CheckCircle2 className="w-4 h-4" /> {t('payValidateMonth')}
            </button>
            <button onClick={() => exportMonthly('ledger')} disabled={busy || payslips.length === 0}
              className="flex items-center gap-2 bg-afmi-gold hover:bg-afmi-darkgold disabled:opacity-40 text-white font-bold px-4 py-2 rounded-xl">
              <Download className="w-4 h-4" /> {t('payLedger')}
            </button>
          </div>
          {activeEmployees.length === 0 && <p className="text-sm text-slate-500">{t('payNoEmployees')}</p>}

          {activeEmployees.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-500 text-xs">
                  <tr>
                    <th className="p-2 text-start">{t('payEmployee')}</th>
                    <th className="p-2">{t('payOvertime25')}</th>
                    <th className="p-2">{t('payBonuses')}</th>
                    <th className="p-2">{t('payExempt')}</th>
                    <th className="p-2 text-end">{t('payGrossTaxable')}</th>
                    <th className="p-2 text-end">IR</th>
                    <th className="p-2 text-end">{t('payNet')}</th>
                    <th className="p-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {activeEmployees.map(emp => {
                    const slip = payslips.find(p => p.employee_id === emp.id);
                    const locked = slip?.status === 'validated';
                    const v = variables[emp.id] || {};
                    return (
                      <tr key={emp.id}>
                        <td className="p-2">
                          <div className="font-semibold text-slate-700">{emp.full_name}</div>
                          <div className="text-[11px] text-slate-400">{emp.matricule} · {fmt(emp.base_salary)} DH</div>
                        </td>
                        {['overtime_hours_25', 'taxable_bonuses', 'exempt_allowances'].map(k => (
                          <td key={k} className="p-2">
                            <input type="number" min="0" disabled={locked} value={v[k] ?? ''} placeholder={String(slip?.inputs?.[k] ?? 0)}
                              onChange={e => setVar(emp.id, k, e.target.value)}
                              className="w-24 rounded-lg border border-slate-200 p-1.5 text-sm disabled:bg-slate-50" />
                          </td>
                        ))}
                        <td className="p-2 text-end">{slip ? fmt(slip.lines.salaire_brut_imposable) : '—'}</td>
                        <td className="p-2 text-end">{slip ? fmt(slip.lines.ir_net) : '—'}</td>
                        <td className="p-2 text-end font-bold text-afmi-forest">{slip ? fmt(slip.lines.net_a_payer) : '—'}</td>
                        <td className="p-2">
                          {slip && (
                            <div className="flex items-center gap-2 justify-end">
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${locked ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                                {locked ? t('payValidated') : t('payDraft')}
                              </span>
                              {slip.warnings.length > 0 && <AlertTriangle className="w-4 h-4 text-amber-500" title={slip.warnings.join('\n')} />}
                              <button onClick={() => exportPayslip(slip.id)} title={t('payPayslip')}>
                                <FileText className="w-4 h-4 text-slate-500 hover:text-afmi-forest" />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ---------------- Employees ---------------- */}
      {tab === 'employees' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <div className="flex justify-between items-center mb-3">
              <h2 className="font-bold text-afmi-forest">{t('payTabEmployees')} ({activeEmployees.length})</h2>
              <button onClick={() => setEditing({ ...EMPTY_EMPLOYEE })}
                className="flex items-center gap-1.5 bg-afmi-forest text-white text-sm font-bold px-3 py-1.5 rounded-lg">
                <Plus className="w-4 h-4" /> {t('payAddEmployee')}
              </button>
            </div>
            <ul className="divide-y divide-slate-100">
              {employees.map(emp => (
                <li key={emp.id} className={`flex items-center justify-between py-2 ${emp.active ? '' : 'opacity-50'}`}>
                  <button className="text-start" onClick={() => setEditing({ ...emp, hire_date: emp.hire_date || "" })}>
                    <div className="font-semibold text-slate-700">{emp.full_name}</div>
                    <div className="text-[11px] text-slate-400">
                      {emp.matricule} · {emp.position || '—'} · {fmt(emp.base_salary)} DH · {emp.dependents} {t('payDependentsShort')}
                      {!emp.cin && ` · ⚠ CIN`}{!emp.cnss_number && ` · ⚠ CNSS`}
                    </div>
                  </button>
                  <button onClick={() => deleteEmployee(emp)}><Trash2 className="w-4 h-4 text-slate-400 hover:text-red-600" /></button>
                </li>
              ))}
            </ul>
          </div>

          {editing && (
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
              <h2 className="font-bold text-afmi-forest">{editing.id ? editing.full_name : t('payAddEmployee')}</h2>
              {[
                ['matricule', t('payMatricule')], ['full_name', t('payFullName')], ['cin', 'CIN'],
                ['cnss_number', t('payCnssNumber')], ['position', t('payPosition')], ['address', t('payAddress')], ['rib', 'RIB'],
              ].map(([k, label]) => (
                <Field key={k} label={label}>
                  <input value={editing[k] || ''} onChange={e => setEditing({ ...editing, [k]: e.target.value })} className={inputCls} />
                </Field>
              ))}
              <Field label={t('payHireDate')}>
                <input type="date" value={editing.hire_date || ''} onChange={e => setEditing({ ...editing, hire_date: e.target.value })} className={inputCls} />
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label={t('payBaseSalary')}>
                  <input type="number" min="0" value={editing.base_salary} onChange={e => setEditing({ ...editing, base_salary: e.target.value })} className={inputCls} />
                </Field>
                <Field label={t('payDependents')}>
                  <input type="number" min="0" max="20" value={editing.dependents} onChange={e => setEditing({ ...editing, dependents: e.target.value })} className={inputCls} />
                </Field>
              </div>
              <Field label={t('payMaritalStatus')}>
                <select value={editing.marital_status || 'celibataire'} onChange={e => setEditing({ ...editing, marital_status: e.target.value })} className={inputCls}>
                  {MARITAL_STATUSES.map(s => <option key={s} value={s}>{t(`payMarital_${s}`)}</option>)}
                </select>
              </Field>
              <Field label={t('payPensionRate')}>
                <input type="number" min="0" max="0.2" step="0.005" value={editing.pension_employee_rate} onChange={e => setEditing({ ...editing, pension_employee_rate: e.target.value })} className={inputCls} />
              </Field>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={editing.cnss_affiliated} onChange={e => setEditing({ ...editing, cnss_affiliated: e.target.checked })} />
                {t('payCnssAffiliated')}
              </label>
              <div className="flex gap-2">
                <button onClick={saveEmployee} disabled={busy}
                  className="flex-1 flex items-center justify-center gap-2 bg-afmi-forest text-white font-bold py-2 rounded-xl">
                  <Save className="w-4 h-4" /> {t('paySave')}
                </button>
                <button onClick={() => setEditing(null)} className="px-4 py-2 rounded-xl border border-slate-300 text-slate-600">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ---------------- Declarations ---------------- */}
      {tab === 'declarations' && (
        <div className="space-y-6">
          <div className="rounded-xl bg-amber-50 border border-amber-200 p-4 text-sm text-amber-900 flex gap-3">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <span>{t('payPortalNotice')}</span>
          </div>

          <div className="flex items-end gap-3">
            <Field label={t('payPeriod')}>
              <input type="month" value={period} onChange={e => setPeriod(e.target.value)} className={inputCls} />
            </Field>
          </div>

          {monthly && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-2">
                <h3 className="font-bold text-afmi-forest">{t('payIrMonthly')} — {period}</h3>
                <div className="text-3xl font-bold text-slate-800">{fmt(monthly.ir.total_withheld)} DH</div>
                <div className="text-xs text-slate-500">{t('payDeadline')} : <b>{monthly.ir.deadline}</b></div>
                <div className="text-[11px] text-slate-400">{monthly.ir.rule}</div>
                {monthly.drafts > 0 && <div className="text-xs text-amber-700">⚠ {monthly.drafts} {t('payDraftsWarning')}</div>}
                <div className="flex flex-wrap gap-2 pt-2">
                  <button onClick={() => exportMonthly('ir')} disabled={!monthly.payslips} className="flex items-center gap-1.5 text-sm font-bold bg-afmi-gold text-white px-3 py-1.5 rounded-lg disabled:opacity-40">
                    <Download className="w-4 h-4" /> {t('payExportStatement')}
                  </button>
                  <button onClick={() => openPortal(monthly.ir.portal)} className="flex items-center gap-1.5 text-sm font-bold bg-afmi-forest text-white px-3 py-1.5 rounded-lg">
                    <ExternalLink className="w-4 h-4" /> {t('payOpenSimpl')}
                  </button>
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-2">
                <h3 className="font-bold text-afmi-forest">{t('payCnssMonthly')} — {period}</h3>
                <div className="text-3xl font-bold text-slate-800">{fmt(monthly.cnss.total_due)} DH</div>
                <div className="text-xs text-slate-500">
                  CNSS {fmt(monthly.cnss.employee + monthly.cnss.employer)} · AF {fmt(monthly.cnss.allocations_familiales)} · TFP {fmt(monthly.cnss.tfp)} · AMO {fmt(monthly.cnss.amo)}
                </div>
                <div className="text-xs text-slate-500">{t('payDeadline')} : <b>{monthly.cnss.deadline}</b></div>
                <div className="text-[11px] text-slate-400">{monthly.cnss.rule}</div>
                {monthly.cnss.missing_cnss_numbers.length > 0 && (
                  <div className="text-xs text-amber-700">⚠ {t('payMissingCnss')} : {monthly.cnss.missing_cnss_numbers.join(', ')}</div>
                )}
                <div className="flex flex-wrap gap-2 pt-2">
                  <button onClick={() => exportMonthly('cnss')} disabled={!monthly.payslips} className="flex items-center gap-1.5 text-sm font-bold bg-afmi-gold text-white px-3 py-1.5 rounded-lg disabled:opacity-40">
                    <Download className="w-4 h-4" /> {t('payExportStatement')}
                  </button>
                  <button onClick={() => openPortal(monthly.cnss.portal)} className="flex items-center gap-1.5 text-sm font-bold bg-afmi-forest text-white px-3 py-1.5 rounded-lg">
                    <ExternalLink className="w-4 h-4" /> {t('payOpenDamancom')}
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <h3 className="font-bold text-afmi-forest">{t('pay9421')}</h3>
              <Field label={t('payYear')}>
                <input type="number" min="2017" max="2100" value={year} onChange={e => setYear(Number(e.target.value))} className={inputCls} />
              </Field>
            </div>
            {annual && (
              <>
                <div className="text-sm text-slate-600">
                  {annual.employees.length} {t('payEmployeesCount')} · IR {fmt(annual.total_ir)} DH · {t('payDeadline')} : <b>{annual.deadline}</b>
                </div>
                {annual.checks.length > 0 && (
                  <ul className="text-xs text-amber-700 list-disc ps-5">
                    {annual.checks.map((c, i) => <li key={i}>{c}</li>)}
                  </ul>
                )}
                <div className="flex flex-wrap gap-2">
                  <button onClick={export9421} disabled={!annual.employees.length} className="flex items-center gap-1.5 text-sm font-bold bg-afmi-gold text-white px-3 py-1.5 rounded-lg disabled:opacity-40">
                    <Download className="w-4 h-4" /> {t('payExport9421')}
                  </button>
                  <button onClick={() => openPortal(annual.portal)} className="flex items-center gap-1.5 text-sm font-bold bg-afmi-forest text-white px-3 py-1.5 rounded-lg">
                    <ExternalLink className="w-4 h-4" /> {t('payOpenSimpl')}
                  </button>
                </div>
              </>
            )}
          </div>

          {/* ---- EDI Simpl-IR (état 9421) ---- */}
          {edi && ediCheck && (
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-bold text-afmi-forest">{t('payEdiTitle')} — {year}</h3>
                <span className="text-[11px] text-slate-400">{ediCheck.spec_version}</span>
              </div>

              <div className={`text-xs rounded-lg p-2 ${ediCheck.schema_file ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>
                {ediCheck.schema_file
                  ? `${t('payEdiSchemaFound')} : ${ediCheck.schema_file}`
                  : <>{t('payEdiSchemaMissing')} <code className="break-all">{edi.schemas_dir}</code></>}
              </div>

              {ediCheck.errors.length > 0 && (
                <div>
                  <div className="text-xs font-bold text-red-700">{t('payEdiBlocking')}</div>
                  <ul className="text-xs text-red-700 list-disc ps-5">{ediCheck.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
                </div>
              )}
              {ediCheck.warnings.length > 0 && (
                <ul className="text-xs text-amber-700 list-disc ps-5">{ediCheck.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
              )}

              <div className="flex flex-wrap gap-2">
                <button onClick={exportEdi} disabled={busy || ediCheck.errors.length > 0}
                  className="flex items-center gap-1.5 text-sm font-bold bg-afmi-forest text-white px-3 py-1.5 rounded-lg disabled:opacity-40">
                  <Download className="w-4 h-4" /> {t('payEdiGenerate')}
                </button>
                <button onClick={() => setShowEdiConfig(!showEdiConfig)}
                  className="text-sm font-bold border border-afmi-forest text-afmi-forest px-3 py-1.5 rounded-lg">
                  {t('payEdiConfig')}
                </button>
              </div>
              <p className="text-[11px] text-slate-400">{t('payEdiHowTo')}</p>

              {showEdiConfig && (
                <div className="border-t border-slate-100 pt-3 space-y-3">
                  <p className="text-[11px] text-slate-500">{t('payEdiCodesHelp')}</p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {EMPLOYER_FIELDS.map(k => (
                      <Field key={k} label={t(`payEdiEmp_${k}`, k)}>
                        <input value={edi.config.employer[k] || ''} placeholder={edi.employer_effective[k] || ''}
                          onChange={e => setEdiField('employer', k, e.target.value)} className={inputCls} />
                      </Field>
                    ))}
                    <Field label={t('payEdiRefTaux')}>
                      <input value={edi.config.codes.ref_taux_permanent || ''}
                        onChange={e => setEdiField('codes', 'ref_taux_permanent', e.target.value)} className={inputCls} />
                    </Field>
                    {MARITAL_STATUSES.map(s => (
                      <Field key={s} label={`${t('payMaritalStatus')} — ${t(`payMarital_${s}`)}`}>
                        <input value={edi.config.codes.situation_familiale[s] || ''}
                          onChange={e => setEdiField('codes', s, e.target.value, 'situation_familiale')} className={inputCls} />
                      </Field>
                    ))}
                    {PAYMENT_METHODS.map(m => (
                      <Field key={m} label={`${t('payPaymentMethod')} — ${t(`payMethod_${m}`)}`}>
                        <input value={edi.config.codes.moyen_paiement[m] || ''}
                          onChange={e => setEdiField('codes', m, e.target.value, 'moyen_paiement')} className={inputCls} />
                      </Field>
                    ))}
                  </div>
                  <button onClick={saveEdiConfig} disabled={busy} className="flex items-center gap-2 bg-afmi-forest text-white text-sm font-bold px-4 py-2 rounded-xl">
                    <Save className="w-4 h-4" /> {t('paySave')}
                  </button>
                </div>
              )}

              {/* IR payments recorded after paying on Simpl-IR (listVersements) */}
              <div className="border-t border-slate-100 pt-3 space-y-2">
                <h4 className="text-sm font-bold text-slate-600">{t('payIrPayments')}</h4>
                {payments.length > 0 && (
                  <table className="w-full text-xs">
                    <tbody className="divide-y divide-slate-100">
                      {payments.map(p => (
                        <tr key={p.id}>
                          <td className="py-1">{p.period}</td>
                          <td className="py-1">{fmt(p.amount)} DH</td>
                          <td className="py-1">{p.payment_date}</td>
                          <td className="py-1">{p.reference} {p.receipt_number && `· ${p.receipt_number}`}</td>
                          <td className="py-1">{t(`payMethod_${p.payment_method}`)}</td>
                          <td className="py-1 text-end">
                            <button onClick={() => deletePayment(p.id)}><Trash2 className="w-3.5 h-3.5 text-slate-400 hover:text-red-600" /></button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <div className="grid grid-cols-2 md:grid-cols-6 gap-2 items-end">
                  <Field label={t('payPeriod')}>
                    <input type="month" value={newPayment.period} onChange={e => setNewPayment({ ...newPayment, period: e.target.value })} className={inputCls} />
                  </Field>
                  <Field label={t('payAmount')}>
                    <input type="number" min="0" value={newPayment.amount} onChange={e => setNewPayment({ ...newPayment, amount: e.target.value })} className={inputCls} />
                  </Field>
                  <Field label={t('payPaymentDate')}>
                    <input type="date" value={newPayment.payment_date} onChange={e => setNewPayment({ ...newPayment, payment_date: e.target.value })} className={inputCls} />
                  </Field>
                  <Field label={t('payReference')}>
                    <input value={newPayment.reference} onChange={e => setNewPayment({ ...newPayment, reference: e.target.value })} className={inputCls} />
                  </Field>
                  <Field label={t('payReceipt')}>
                    <input value={newPayment.receipt_number} onChange={e => setNewPayment({ ...newPayment, receipt_number: e.target.value })} className={inputCls} />
                  </Field>
                  <Field label={t('payPaymentMethod')}>
                    <select value={newPayment.payment_method} onChange={e => setNewPayment({ ...newPayment, payment_method: e.target.value })} className={inputCls}>
                      {PAYMENT_METHODS.map(m => <option key={m} value={m}>{t(`payMethod_${m}`)}</option>)}
                    </select>
                  </Field>
                </div>
                <button onClick={addPayment} disabled={busy || !newPayment.period || !newPayment.amount || !newPayment.payment_date}
                  className="flex items-center gap-1.5 text-sm font-bold bg-afmi-gold text-white px-3 py-1.5 rounded-lg disabled:opacity-40">
                  <Plus className="w-4 h-4" /> {t('payAddPayment')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ---------------- Simulator ---------------- */}
      {tab === 'simulator' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
            <Field label={t('payPeriod')}>
              <input type="month" value={sim.period} onChange={e => setSim({ ...sim, period: e.target.value })} className={inputCls} />
            </Field>
            <Field label={t('payRulesVersion')}>
              <select value={sim.rules_version} onChange={e => setSim({ ...sim, rules_version: e.target.value })} className={inputCls}>
                <option value="">{t('payRulesAuto')}</option>
                {rules?.versions.map(v => <option key={v.id} value={v.id}>{v.label}</option>)}
              </select>
            </Field>
            <Field label={t('payBaseSalary')}>
              <input type="number" min="0" value={sim.base_salary} onChange={e => setSim({ ...sim, base_salary: e.target.value })} className={inputCls} />
            </Field>
            <Field label={t('payDependents')}>
              <input type="number" min="0" max="20" value={sim.dependents} onChange={e => setSim({ ...sim, dependents: e.target.value })} className={inputCls} />
            </Field>
            <Field label={t('payHireDate')}>
              <input type="date" value={sim.hire_date} onChange={e => setSim({ ...sim, hire_date: e.target.value })} className={inputCls} />
            </Field>
            <button onClick={simulate} disabled={busy} className="w-full flex items-center justify-center gap-2 bg-afmi-forest text-white font-bold py-2 rounded-xl">
              <Calculator className="w-4 h-4" /> {t('paySimulate')}
            </button>
          </div>
          {simResult && (
            <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
              <div className="text-xs text-slate-400 mb-2">
                {rules?.versions.find(v => v.id === simResult.rules_version)?.label} — {rules?.versions.find(v => v.id === simResult.rules_version)?.legal_ref}
              </div>
              <table className="w-full text-sm">
                <tbody className="divide-y divide-slate-100">
                  {Object.entries(simResult.lines).filter(([, v]) => v !== 0).map(([k, v]) => (
                    <tr key={k} className={['net_a_payer', 'ir_net', 'cout_total_employeur'].includes(k) ? 'font-bold text-afmi-forest' : ''}>
                      <td className="py-1.5">{t(`payLine_${k}`, k)}</td>
                      <td className="py-1.5 text-end">{fmt(v)} DH</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {simResult.warnings.map((w, i) => <div key={i} className="text-xs text-amber-700 mt-2">⚠ {w}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
