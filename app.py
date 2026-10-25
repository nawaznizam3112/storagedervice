import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from autoclave.rules import (
    COLUMNS,
    CYCLE_TYPES,
    autoclave_status,
    effective,
    evaluate_cycle,
    prep,
    recall_scope,
)
from autoclave.storage import GitHubStore, LocalStore

IST = ZoneInfo("Asia/Kolkata")
st.set_page_config(page_title="Autoclave Cycle Log", page_icon="🧼", layout="wide")


def cfg(key, default=""):
    if os.environ.get(key):
        return os.environ[key]
    try:
        return st.secrets[key]
    except Exception:
        return default


@st.cache_resource
def get_store():
    token, repo = cfg("GITHUB_TOKEN"), cfg("GITHUB_REPO")
    if token and repo:
        return GitHubStore(token, repo, cfg("DATA_PATH", "data/cycles.csv"), cfg("GITHUB_BRANCH", "main"))
    return LocalStore(cfg("DATA_PATH", "data/cycles.csv"))


@st.cache_data(ttl=60)
def load_raw():
    return get_store().load()


def save(row, message):
    get_store().append(row, message)
    load_raw.clear()


def unlocked():
    pin = cfg("APP_PIN")
    if not pin or st.session_state.get("ok"):
        return True
    entered = st.text_input("Staff PIN", type="password")
    if entered and entered == pin:
        st.session_state["ok"] = True
        st.rerun()
    elif entered:
        st.error("Wrong PIN.")
    return False


raw = load_raw()
df = prep(raw)
eff = effective(df)
machines = sorted(set(cfg("AUTOCLAVES", "Autoclave 1").split(",")) | set(eff["autoclave_id"]) - {""})
machines = [m.strip() for m in machines]

st.title("🧼 Autoclave Cycle Log")
st.caption("Append-only sterilisation record with traceability. Corrections are new "
           "entries that supersede, never edits. Do not enter patient names: "
           "record instrument-set / pack IDs and put the pack ID in the patient chart.")
if isinstance(get_store(), LocalStore):
    st.info("Local mode: data saved to a CSV on this machine. Add GitHub secrets to deploy.")

tab_dash, tab_log, tab_fix, tab_trace = st.tabs(
    ["📊 Dashboard", "➕ Log a cycle", "✏️ Correct / add BI result", "🔎 Trace & export"])

# ---------------- Dashboard ----------------
with tab_dash:
    now = pd.Timestamp.now(tz="UTC")
    for ac in machines:
        st.subheader(ac)
        for level, msg in autoclave_status(df, ac, now):
            {"ok": st.success, "info": st.info, "warning": st.warning, "error": st.error}[level](msg)
        f, scope, resolved = recall_scope(df, ac)
        if f is not None:
            with st.expander(f"Recall scope for latest BI failure (cycle {int(f['cycle_no'])})"
                             + (", later BI passed" if resolved else ", UNRESOLVED")):
                st.dataframe(scope[["cycle_no", "start", "load_contents", "result"]],
                             hide_index=True, width="stretch")
    e = eff.copy()
    if not e.empty:
        e["day"] = e["start"].dt.tz_convert(IST).dt.date
        last30 = e[e["start"] > now - pd.Timedelta(days=30)]
        c1, c2, c3 = st.columns(3)
        c1.metric("Cycles (30 d)", len(last30))
        c2.metric("Failed cycles (30 d)", int((last30["result"] == "Fail").sum()))
        c3.metric("Pass rate (30 d)", f"{(last30['result'] == 'Pass').mean() * 100:.1f}%" if len(last30) else "–")
        st.altair_chart(
            alt.Chart(last30).mark_bar().encode(
                x=alt.X("day:T", title=None), y=alt.Y("count():Q", title="Cycles"),
                color=alt.Color("result:N", scale=alt.Scale(domain=["Pass", "Fail"], range=["#2e8b57", "#d62728"])),
            ).properties(height=240), width="stretch")
        st.markdown("**Latest cycles**")
        show = e.sort_values("start", ascending=False).head(20)
        st.dataframe(show[["start", "autoclave_id", "cycle_no", "cycle_type", "temp_c", "hold_min",
                           "chem_indicator", "bowie_dick", "bio_indicator", "result", "load_contents"]],
                     hide_index=True, width="stretch")

# ---------------- Log a cycle ----------------
with tab_log:
    if unlocked():
        with st.form("log_cycle", clear_on_submit=True):
            a, b, c = st.columns(3)
            ac = a.selectbox("Autoclave", machines)
            operator = b.text_input("Operator (initials)")
            cycle_no = c.number_input("Machine cycle counter (from printout)", min_value=0, step=1)
            d1, d2, d3 = st.columns(3)
            date = d1.date_input("Cycle date", value=datetime.now(IST).date())
            time = d2.time_input("Start time", value=datetime.now(IST).time().replace(second=0, microsecond=0))
            ctype = d3.selectbox("Cycle type", list(CYCLE_TYPES))
            p1, p2, p3 = st.columns(3)
            temp = p1.number_input("Max temperature (°C)", 0.0, 200.0, 134.0, 0.1)
            hold = p2.number_input("Hold / plateau time (min)", 0.0, 120.0, 4.0, 0.5)
            pres = p3.number_input("Pressure (kPa, optional)", 0.0, 500.0, 0.0, 1.0)
            i1, i2, i3 = st.columns(3)
            chem = i1.selectbox("Chemical indicator", ["Pass", "Fail", "N/A"])
            bd = i2.selectbox("Air-removal test (Bowie-Dick/Helix)", ["Not run", "Pass", "Fail"])
            bio = i3.selectbox("Biological indicator", ["Not run", "Pending", "Pass", "Fail"])
            load = st.text_area("Load contents / pack IDs (no patient names)")
            ref = st.text_input("Printout reference (e.g. filename, sticker or filing no.)")
            notes = st.text_input("Notes")
            go = st.form_submit_button("Save cycle")
        if go:
            dupe = eff[(eff["autoclave_id"] == ac) & (eff["cycle_no"] == cycle_no)]
            if not operator.strip() or not load.strip():
                st.error("Operator and load contents are required.")
            elif not dupe.empty:
                st.error(f"Cycle {cycle_no} already logged for {ac}. Use the Correct tab to amend it.")
            else:
                result, reasons = evaluate_cycle(ctype, temp, hold, chem)
                start = datetime.combine(date, time, tzinfo=IST).astimezone(timezone.utc)
                row = dict.fromkeys(COLUMNS, "")
                row.update(entry_id=uuid.uuid4().hex[:10], logged_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           operator=operator.strip().upper(), autoclave_id=ac, cycle_no=int(cycle_no),
                           cycle_start_utc=start.isoformat(timespec="seconds"), cycle_type=ctype, temp_c=temp,
                           hold_min=hold, pressure_kpa=pres or "", chem_indicator=chem, bowie_dick=bd,
                           bio_indicator=bio, load_contents=load.strip(), printout_ref=ref.strip(),
                           result=result, fail_reasons="; ".join(reasons), notes=notes.strip())
                try:
                    save(row, f"cycle {int(cycle_no)} {ac} {result} by {row['operator']}")
                    if result == "Fail":
                        st.error("CYCLE FAILED: " + "; ".join(reasons) + ". Do NOT release this load; reprocess.")
                    else:
                        st.success("Saved. Cycle parameters within limits.")
                except Exception as ex:
                    st.error(f"Could not save: {ex}")

# ---------------- Correct / add BI result ----------------
with tab_fix:
    if unlocked():
        st.write("Biological indicators are read 24-48 h later (rapid ones sooner): log the cycle as "
                 "**Pending**, then add the result here. Mistakes are also fixed here; the original stays in the audit trail.")
        pick = eff.sort_values("start", ascending=False).head(60)
        if pick.empty:
            st.write("Nothing logged yet.")
        else:
            labels = {r.entry_id: f"{r.start.astimezone(IST):%d %b %H:%M} | {r.autoclave_id} #{int(r.cycle_no)} | "
                                  f"BI: {r.bio_indicator} | {r.load_contents[:40]}" for r in pick.itertuples()}
            with st.form("fix"):
                eid = st.selectbox("Entry", list(labels), format_func=labels.get)
                n1, n2 = st.columns(2)
                new_bio = n1.selectbox("Biological indicator", ["(unchanged)", "Not run", "Pending", "Pass", "Fail"])
                new_chem = n2.selectbox("Chemical indicator", ["(unchanged)", "Pass", "Fail", "N/A"])
                reason = st.text_input("Reason for change (required)")
                who = st.text_input("Your initials")
                go2 = st.form_submit_button("Save correction")
            if go2:
                if not reason.strip() or not who.strip():
                    st.error("Reason and initials are required.")
                else:
                    row = pick[pick["entry_id"] == eid].iloc[0][COLUMNS].to_dict()
                    if new_bio != "(unchanged)":
                        row["bio_indicator"] = new_bio
                    if new_chem != "(unchanged)":
                        row["chem_indicator"] = new_chem
                    res, rs = evaluate_cycle(row["cycle_type"], float(row["temp_c"]), float(row["hold_min"]), row["chem_indicator"])
                    row.update(result=res, fail_reasons="; ".join(rs), corrects_entry_id=eid,
                               correction_reason=reason.strip(), operator=who.strip().upper(),
                               entry_id=uuid.uuid4().hex[:10],
                               logged_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               cycle_start_utc=pick[pick["entry_id"] == eid].iloc[0]["start"].isoformat(timespec="seconds"))
                    try:
                        save(row, f"correction of {eid}: {reason.strip()[:60]}")
                        st.success("Correction saved." if new_bio != "Fail" else "BI FAILED: see dashboard for recall scope.")
                    except Exception as ex:
                        st.error(f"Could not save: {ex}")

# ---------------- Trace & export ----------------
with tab_trace:
    q = st.text_input("Trace a pack / instrument-set ID or any load text")
    if q:
        hits = eff[eff["load_contents"].str.contains(q, case=False, na=False)]
        st.write(f"{len(hits)} cycle(s) contained '{q}'")
        st.dataframe(hits[["start", "autoclave_id", "cycle_no", "result", "bio_indicator", "operator", "load_contents", "printout_ref"]],
                     hide_index=True, width="stretch")
    st.divider()
    month = st.text_input("Export month (YYYY-MM)", value=datetime.now(IST).strftime("%Y-%m"))
    if not eff.empty:
        m = eff[eff["start"].dt.tz_convert(IST).dt.strftime("%Y-%m") == month]
        st.download_button(f"Download {month} register ({len(m)} cycles)",
                           m.drop(columns=["start"]).to_csv(index=False), f"autoclave_{month}.csv", "text/csv")
    with st.expander("Full audit trail (including superseded entries)"):
        st.dataframe(df.drop(columns=["start"]), hide_index=True, width="stretch")
