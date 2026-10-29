import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowDownLeft, ArrowLeftRight, ArrowUpRight, CalendarDays, CheckCircle2,
  ChevronLeft, ChevronRight, CircleDollarSign, CreditCard, LayoutDashboard,
  LoaderCircle, Menu, Plus, RefreshCw, Search, Send, ShieldCheck, Sparkles,
  TrendingUp, WalletCards, X,
} from "lucide-react";
import { formatINR } from "./utils/currency";

type Account = { id: string; name: string; balance: string; created_at: string };
type Balance = { account_id: string; balance: string };
type Transaction = {
  id: string; account_id: string; type: "credit" | "debit"; amount: string;
  description: string; reference_id: string; created_at: string;
};
type History = {
  account_id: string; current_page: number; page_size: number;
  total_records: number; total_pages: number; results: Transaction[];
};
type ApiError = { error?: { message?: string; details?: { field: string; message: string }[] } };
type Notice = { type: "success" | "error"; text: string };

const configuredApiBase = import.meta.env.VITE_API_BASE_URL;
const API_BASE = (configuredApiBase || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")).replace(/\/$/, "");
const accountKey = "ledgerly-account";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    if (!API_BASE) throw new Error("VITE_API_BASE_URL is required for the production frontend build.");
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
    const payload = (await response.json().catch(() => null)) as ApiError | T | null;
    if (!response.ok) {
      const error = payload as ApiError | null;
      const detail = error?.error?.details?.map((item) => item.message).join(" ") || error?.error?.message;
      throw new Error(detail || `Request failed (${response.status}).`);
    }
    return payload as T;
  } catch (error) {
    if (error instanceof TypeError) throw new Error("Unable to reach the ledger API. Check that the backend is running.");
    throw error;
  }
}

function dateLabel(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit", month: "short", year: "numeric", hour: "numeric", minute: "2-digit",
  }).format(new Date(value));
}

function Field({ label, hint, ...props }: { label: string; hint?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return <label className="field"><span>{label}{hint && <small>{hint}</small>}</span><input {...props} /></label>;
}

function NoticeIcon({ type }: { type: Notice["type"] }) {
  return type === "success" ? <CheckCircle2 size={17} /> : <Sparkles size={17} />;
}

function App() {
  const [account, setAccount] = useState<Account | null>(() => {
    try { return JSON.parse(localStorage.getItem(accountKey) || "null") as Account | null; } catch { return null; }
  });
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [balance, setBalance] = useState<Balance | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [filter, setFilter] = useState<"all" | "credit" | "debit">("all");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formBusy, setFormBusy] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [accountForm, setAccountForm] = useState({ name: "" });
  const [transactionForm, setTransactionForm] = useState({ type: "credit", amount: "", description: "", reference_id: "" });
  const [transferForm, setTransferForm] = useState({ destination_account_id: "", amount: "", description: "", reference_id: "" });

  const refreshAccounts = useCallback(async () => {
    try {
      const available = await request<Account[]>("/api/accounts/");
      setAccounts(available);
      if (account) {
        const freshAccount = available.find((item) => item.id === account.id);
        if (freshAccount && (freshAccount.balance !== account.balance || freshAccount.name !== account.name)) {
          setAccount(freshAccount);
          localStorage.setItem(accountKey, JSON.stringify(freshAccount));
        } else if (!freshAccount) {
          setAccount(null);
          localStorage.removeItem(accountKey);
        }
      } else if (available[0]) {
        setAccount(available[0]);
        localStorage.setItem(accountKey, JSON.stringify(available[0]));
      }
    } catch (error) {
      setNotice({ type: "error", text: error instanceof Error ? error.message : "Could not load available accounts." });
    }
  }, [account]);

  const refresh = useCallback(async () => {
    if (!account) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: String(page), limit: "8" });
      if (filter !== "all") params.set("type", filter);
      if (search.trim()) params.set("search", search.trim());
      if (dateFrom) params.set("date_from", `${dateFrom}T00:00:00+00:00`);
      if (dateTo) params.set("date_to", `${dateTo}T23:59:59+00:00`);
      const [nextBalance, nextHistory] = await Promise.all([
        request<Balance>(`/api/accounts/${account.id}/balance`),
        request<History>(`/api/accounts/${account.id}/transactions/?${params.toString()}`),
      ]);
      setBalance(nextBalance); setHistory(nextHistory);
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Could not load account data." }); }
    finally { setLoading(false); }
  }, [account, dateFrom, dateTo, filter, page, search]);

  useEffect(() => { void refreshAccounts(); }, [refreshAccounts]);
  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 4500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const currentBalance = balance?.balance || account?.balance || "0.00";
  const credits = history?.results.filter((item) => item.type === "credit").length || 0;
  const debits = history?.results.filter((item) => item.type === "debit").length || 0;

  async function submitAccount(event: FormEvent) {
    event.preventDefault(); setFormBusy(true);
    try {
      const created = await request<Account>("/api/accounts/", { method: "POST", body: JSON.stringify(accountForm) });
      setAccounts((current) => [...current, created]);
      setAccount(created); localStorage.setItem(accountKey, JSON.stringify(created)); setAccountForm({ name: "" });
      setNotice({ type: "success", text: `Account "${created.name}" is ready.` });
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Could not create account." }); }
    finally { setFormBusy(false); }
  }

  async function submitTransaction(event: FormEvent) {
    event.preventDefault(); if (!account) return; setFormBusy(true);
    try {
      await request<Transaction>(`/api/accounts/${account.id}/transactions/`, { method: "POST", body: JSON.stringify(transactionForm) });
      setTransactionForm({ ...transactionForm, amount: "", description: "", reference_id: "" }); setPage(1);
      setNotice({ type: "success", text: `${transactionForm.type === "credit" ? "Credit" : "Debit"} posted in INR.` });
      await refresh();
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Could not post transaction." }); }
    finally { setFormBusy(false); }
  }

  async function submitTransfer(event: FormEvent) {
    event.preventDefault(); if (!account) return; setFormBusy(true);
    if (!transferForm.destination_account_id || transferForm.destination_account_id === account.id) {
      setNotice({ type: "error", text: "Choose a recipient account different from the sender." });
      setFormBusy(false);
      return;
    }
    if (!transferForm.amount || Number(transferForm.amount) <= 0 || !/^\d+(\.\d{1,2})?$/.test(transferForm.amount)) {
      setNotice({ type: "error", text: "Enter a positive INR amount with at most two decimal places." });
      setFormBusy(false);
      return;
    }
    try {
      await request("/api/transfers/", { method: "POST", body: JSON.stringify({ source_account_id: account.id, ...transferForm }) });
      setTransferForm({ destination_account_id: "", amount: "", description: "", reference_id: "" });
      setNotice({ type: "success", text: "INR transfer completed successfully." }); setPage(1); await refreshAccounts(); await refresh();
    } catch (error) { setNotice({ type: "error", text: error instanceof Error ? error.message : "Could not complete transfer." }); }
    finally { setFormBusy(false); }
  }

  const nav = <nav className="space-y-1">
    <a className="nav-item active" href="#overview" onClick={() => setMobileNav(false)}><LayoutDashboard size={18} /> Overview</a>
    <a className="nav-item" href="#activity" onClick={() => setMobileNav(false)}><ArrowLeftRight size={18} /> Activity</a>
    <a className="nav-item" href="#actions" onClick={() => setMobileNav(false)}><WalletCards size={18} /> Move money</a>
  </nav>;

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? "open" : ""}`}>
      <div className="brand"><div className="brand-mark"><CircleDollarSign size={23} /></div><div><strong>ledgerly</strong><small>Transaction workspace</small></div></div>
      <div className="sidebar-label">Workspace</div>{nav}
      <div className="sidebar-foot"><ShieldCheck size={17} /><span>Secure by design<br /><small>Atlas-connected ledger</small></span></div>
    </aside>
    {mobileNav && <button className="scrim" onClick={() => setMobileNav(false)} aria-label="Close navigation" />}
    <main className="main-shell">
      <header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(true)} aria-label="Open navigation"><Menu /></button><div><p className="eyebrow">PERSONAL FINANCE</p><h1>Good morning{account ? `, ${account.name.split(" ")[0]}` : ""}.</h1></div><div className="topbar-actions"><button className="icon-button" onClick={() => void refresh()} disabled={loading} aria-label="Refresh dashboard"><RefreshCw size={18} className={loading ? "spin" : ""} /></button><div className="avatar">{account?.name?.slice(0, 1).toUpperCase() || "L"}</div></div></header>
      {notice && <div className={`toast ${notice.type}`} role="status"><NoticeIcon type={notice.type} />{notice.text}<button onClick={() => setNotice(null)} aria-label="Dismiss notification"><X size={16} /></button></div>}
      {account && <section className="account-switcher panel">
        <div><span className="section-kicker">ACTIVE ACCOUNT</span><h2>{account.name}</h2><p>{account.id}</p></div>
        <label className="account-select"><span>Sender account</span><select value={account.id} onChange={(event) => {
          const selected = accounts.find((item) => item.id === event.target.value);
          if (selected) { setAccount(selected); localStorage.setItem(accountKey, JSON.stringify(selected)); setPage(1); }
        }}><option value="" disabled>Select an account</option>{accounts.map((item) => <option value={item.id} key={item.id}>{item.name} · {formatINR(item.balance)}</option>)}</select></label>
        <button className="outline-button" onClick={() => setAccount(null)}><Plus size={16} /> Create Account</button>
      </section>}
      {!account ? <section className="welcome-card"><div className="welcome-copy"><span className="pill">Your financial command center</span><h2>Make every movement<br /><em>count.</em></h2><p>Create your first account to start tracking your INR balance, transactions, and transfers in one clear view.</p></div><form className="account-form" onSubmit={submitAccount}><div className="form-icon"><Plus size={20} /></div><h3>Create an account</h3><p>Start with a name you will recognize.</p><Field label="Account name" placeholder="e.g. Main checking" value={accountForm.name} onChange={(e) => setAccountForm({ name: e.target.value })} required /><button className="primary-button" disabled={formBusy}>{formBusy ? <LoaderCircle className="spin" size={17} /> : <Plus size={17} />} Create account</button></form></section> :
      <>
        <section id="overview" className="hero-grid"><div className="balance-card"><div className="card-top"><span className="pill light">AVAILABLE BALANCE · INR</span><button className="card-refresh" onClick={() => void refresh()} aria-label="Refresh balance"><RefreshCw size={16} /></button></div><div className="balance-value">{formatINR(currentBalance)}</div><p className="balance-meta"><TrendingUp size={15} /> Live balance · {account.name}</p><div className="balance-line"><span /><span /><span /><span /><span /></div></div><div className="stat-card"><div className="stat-icon mint"><ArrowDownLeft size={18} /></div><span className="stat-label">Credits shown</span><strong>{credits}</strong><small>on this page</small></div><div className="stat-card"><div className="stat-icon coral"><ArrowUpRight size={18} /></div><span className="stat-label">Debits shown</span><strong>{debits}</strong><small>on this page</small></div></section>
        <section id="actions" className="section-grid"><div className="panel"><div className="panel-heading"><div><span className="section-kicker">QUICK ACTION</span><h2>Post a transaction</h2></div><div className="segmented"><button type="button" className={transactionForm.type === "credit" ? "selected credit" : ""} onClick={() => setTransactionForm({ ...transactionForm, type: "credit" })}><ArrowDownLeft size={15} /> Credit</button><button type="button" className={transactionForm.type === "debit" ? "selected debit" : ""} onClick={() => setTransactionForm({ ...transactionForm, type: "debit" })}><ArrowUpRight size={15} /> Debit</button></div></div><form onSubmit={submitTransaction} className="form-grid"><Field label="Amount" hint="INR" type="number" min="0.01" step="0.01" placeholder="₹ 0.00" value={transactionForm.amount} onChange={(e) => setTransactionForm({ ...transactionForm, amount: e.target.value })} required /><Field label="Description" placeholder="What is this for?" value={transactionForm.description} onChange={(e) => setTransactionForm({ ...transactionForm, description: e.target.value })} required /><Field label="Reference ID" placeholder="Unique reference" value={transactionForm.reference_id} onChange={(e) => setTransactionForm({ ...transactionForm, reference_id: e.target.value })} required /><button className="primary-button wide" disabled={formBusy}>{formBusy ? <LoaderCircle className="spin" size={17} /> : <CreditCard size={17} />} Post {transactionForm.type}</button></form></div>
        <div className="panel"><div className="panel-heading"><div><span className="section-kicker">MOVE MONEY</span><h2>Transfer INR</h2></div><Send size={20} className="heading-icon" /></div><form onSubmit={submitTransfer} className="form-grid"><label className="field"><span>Recipient account</span><select value={transferForm.destination_account_id} onChange={(e) => setTransferForm({ ...transferForm, destination_account_id: e.target.value })} required><option value="">Choose a recipient</option>{accounts.filter((item) => item.id !== account.id).map((item) => <option key={item.id} value={item.id}>{item.name} · {formatINR(item.balance)}</option>)}</select></label><Field label="Amount" hint="INR" type="number" min="0.01" step="0.01" placeholder="₹ 0.00" value={transferForm.amount} onChange={(e) => setTransferForm({ ...transferForm, amount: e.target.value })} required /><Field label="Description" placeholder="Reason for transfer" value={transferForm.description} onChange={(e) => setTransferForm({ ...transferForm, description: e.target.value })} required /><Field label="Reference ID" placeholder="Unique reference" value={transferForm.reference_id} onChange={(e) => setTransferForm({ ...transferForm, reference_id: e.target.value })} required /><button className="secondary-button wide" disabled={formBusy || accounts.length < 2}>{formBusy ? <LoaderCircle className="spin" size={17} /> : <Send size={17} />} {accounts.length < 2 ? "Create another account to transfer" : "Send transfer"}</button></form></div></section>
        <section id="activity" className="panel activity-panel"><div className="activity-header"><div><span className="section-kicker">ACCOUNT ACTIVITY</span><h2>Transaction history</h2></div><div className="filter-tabs">{(["all", "credit", "debit"] as const).map((item) => <button key={item} onClick={() => { setFilter(item); setPage(1); }} className={filter === item ? "active" : ""}>{item}</button>)}</div></div><div className="history-tools"><label className="search-field"><Search size={16} /><input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search description or reference" aria-label="Search transaction history" /></label><label className="date-field"><CalendarDays size={15} /><input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} aria-label="Transactions from date" /></label><label className="date-field"><CalendarDays size={15} /><input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} aria-label="Transactions to date" /></label></div>{loading && !history ? <div className="loading-state"><LoaderCircle className="spin" /> Loading activity...</div> : history?.results.length ? <><div className="table-wrap"><table><thead><tr><th>Transaction</th><th>Reference</th><th>Date</th><th className="align-right">Amount</th></tr></thead><tbody>{history.results.map((item) => <tr key={item.id}><td><div className="transaction-name"><span className={`transaction-icon ${item.type}`}>{item.type === "credit" ? <ArrowDownLeft size={16} /> : <ArrowUpRight size={16} />}</span><span><strong>{item.description}</strong><small>{item.type} · {item.id.slice(0, 16)}</small></span></div></td><td className="muted">{item.reference_id}</td><td className="muted">{dateLabel(item.created_at)}</td><td className={`align-right amount ${item.type}`}>{item.type === "credit" ? "+" : "-"}{formatINR(item.amount)}</td></tr>)}</tbody></table></div><div className="pagination"><span>Showing {history.results.length} of {history.total_records} transactions</span><div><button disabled={page <= 1} onClick={() => setPage(page - 1)} aria-label="Previous page"><ChevronLeft size={16} /></button><b>{page}</b><button disabled={page >= history.total_pages} onClick={() => setPage(page + 1)} aria-label="Next page"><ChevronRight size={16} /></button></div></div></> : <div className="empty-state"><ArrowLeftRight size={25} /><strong>No transactions found</strong><span>Try changing your filters or post your first INR transaction.</span></div>}</section>
      </>}
      <footer>Ledgerly · INR ledger connected to FastAPI</footer>
    </main>
  </div>;
}

export default App;
