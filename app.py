import os
import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Clinic Environment Monitor", page_icon="🌡️", layout="wide")

# Data source: local CSV by default; set DATA_URL (env or Streamlit secret) to the
# raw GitHub URL of data/readings.csv when deployed.
def _data_url():
    if os.environ.get("DATA_URL"):
        return os.environ["DATA_URL"]
    try:
        return st.secrets["DATA_URL"]
    except Exception:  # no secrets file or key -> local CSV
        return "data/readings.csv"


DATA_URL = _data_url()


@st.cache_data(ttl=300)
def load(src: str) -> pd.DataFrame:
    df = pd.read_csv(src, parse_dates=["timestamp_utc"])
    df["time"] = df["timestamp_utc"].dt.tz_convert("Asia/Kolkata")
    return df.sort_values("time").reset_index(drop=True)


def flag(df, t_lo, t_hi, h_lo, h_hi):
    df = df.copy()
    df["temp_ok"] = df["temperature_c"].between(t_lo, t_hi)
    df["hum_ok"] = df["humidity_pct"].between(h_lo, h_hi)
    df["in_spec"] = df["temp_ok"] & df["hum_ok"]
    return df


st.title("🌡️ Clinic Environment Monitor")
st.caption("Storage-area temperature and humidity with excursion tracking.")

try:
    df = load(DATA_URL)
except Exception as e:
    st.error(f"Could not load data from `{DATA_URL}`: {e}")
    st.info("Run `python collector/collector.py --backfill 72` to create sample data.")
    st.stop()

with st.sidebar:
    st.header("Acceptable range")
    t_lo, t_hi = st.slider("Temperature (°C)", 0.0, 40.0, (15.0, 30.0))
    h_lo, h_hi = st.slider("Humidity (%RH)", 0, 100, (30, 70))
    days = st.selectbox("Window", [1, 3, 7, 30], index=1, format_func=lambda d: f"Last {d} day(s)")

df = flag(df, t_lo, t_hi, h_lo, h_hi)
cutoff = df["time"].max() - pd.Timedelta(days=days)
w = df[df["time"] >= cutoff]
last = df.iloc[-1]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Temperature", f"{last.temperature_c} °C")
c2.metric("Humidity", f"{last.humidity_pct} %RH")
c3.metric("In spec (window)", f"{w.in_spec.mean() * 100:.1f}%")
c4.metric("Excursions (window)", int((~w.in_spec).sum()))

age_min = (pd.Timestamp.now(tz="UTC") - last.timestamp_utc).total_seconds() / 60
if not last.in_spec:
    st.error("🚨 Latest reading is OUT of range.")
elif age_min > 60:
    st.warning(f"⚠️ No new reading for {age_min / 60:.1f} h. Check the device.")
else:
    st.success("✅ Latest reading in range.")

def chart(col, lo, hi, title):
    base = alt.Chart(w).mark_line().encode(
        x=alt.X("time:T", title=None), y=alt.Y(f"{col}:Q", title=title, scale=alt.Scale(zero=False)))
    rules = alt.Chart(pd.DataFrame({"y": [lo, hi]})).mark_rule(color="red", strokeDash=[5, 5]).encode(y="y:Q")
    return (base + rules).properties(height=260)

l, r = st.columns(2)
l.altair_chart(chart("temperature_c", t_lo, t_hi, "°C"), width="stretch")
r.altair_chart(chart("humidity_pct", h_lo, h_hi, "%RH"), width="stretch")

st.subheader("Excursion log")
exc = w[~w.in_spec][["time", "temperature_c", "humidity_pct", "temp_ok", "hum_ok"]]
if exc.empty:
    st.write("No excursions in this window.")
else:
    st.dataframe(exc.rename(columns={"temp_ok": "temp in range", "hum_ok": "humidity in range"}),
                 width="stretch", hide_index=True)

st.download_button("Download window as CSV", w.to_csv(index=False), "readings_window.csv", "text/csv")
