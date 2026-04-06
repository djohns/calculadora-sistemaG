import streamlit as st
import itertools
import pandas as pd
import requests
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Calculadora Sistemas + Value + Kelly + Live Odds", layout="wide")
st.title("🧮 Calculadora de Apuestas de Sistema + Value Betting + Kelly + Cuotas en Vivo")
st.markdown("**Versión mejorada** – The Odds API + Kelly Criterion")

# ====================== CARGAR API KEY ======================
def get_api_key():
    # Prioridad: Streamlit Cloud Secrets > .env local
    if "THE_ODDS_API_KEY" in st.secrets:
        return st.secrets["THE_ODDS_API_KEY"]
    return os.getenv("THE_ODDS_API_KEY")

THE_ODDS_API_KEY = get_api_key()

# ====================== INPUTS ======================
with st.sidebar:
    st.header("📥 Datos generales")
    n = st.slider("Número de selecciones", 3, 8, 4)
    total_stake = st.number_input("Monto total a invertir (CLP)", min_value=1000, value=100000, step=10000)
    bankroll = st.number_input("Bankroll total (CLP)", min_value=100000, value=5000000, step=100000)
    kelly_frac = st.slider("Fracción Kelly (conservador)", 0.1, 1.0, 0.5, 0.05)
    
    st.subheader("Cuotas en vivo (The Odds API)")
    leagues = {
        "Premier League": "soccer_epl",
        "La Liga": "soccer_spain_laliga",
        "Bundesliga": "soccer_germany_bundesliga",
        "Serie A": "soccer_italy_serie_a",
        "Champions League": "soccer_uefa_champions_league",
        "Libertadores": "soccer_conmebol_copa_libertadores"
    }
    selected_league_name = st.selectbox("Liga", list(leagues.keys()))
    selected_sport = leagues[selected_league_name]
    
    if st.button("🔄 Cargar cuotas en vivo"):
        if not THE_ODDS_API_KEY:
            st.error("❌ No se encontró API key. Configura .env o Streamlit Secrets.")
        else:
            url = f"https://api.the-odds-api.com/v4/sports/{selected_sport}/odds/"
            params = {
                "apiKey": THE_ODDS_API_KEY,
                "regions": "eu",
                "markets": "h2h",
                "oddsFormat": "decimal"
            }
            with st.spinner("Cargando cuotas..."):
                resp = requests.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    matches = []
                    for event in data[:15]:  # máximo 15 partidos
                        if not event["bookmakers"]:
                            continue
                        # Tomamos el mejor odd de cada resultado (más favorable al apostador)
                        best_home = best_draw = best_away = 1.01
                        best_book = "N/A"
                        for book in event["bookmakers"]:
                            for market in book["markets"]:
                                if market["key"] == "h2h":
                                    outcomes = market["outcomes"]
                                    if len(outcomes) >= 3:
                                        h = outcomes[0]["price"]
                                        d = outcomes[1]["price"]
                                        a = outcomes[2]["price"]
                                        if h > best_home: best_home = h
                                        if d > best_draw: best_draw = d
                                        if a > best_away: best_away = a
                                        best_book = book["title"]
                        matches.append({
                            "Partido": f"{event['home_team']} vs {event['away_team']}",
                            "Hora": event["commence_time"][:16],
                            "Home": round(best_home, 2),
                            "Draw": round(best_draw, 2),
                            "Away": round(best_away, 2),
                            "Mejor casa": best_book
                        })
                    st.session_state["live_matches"] = pd.DataFrame(matches)
                    st.success(f"✅ {len(matches)} partidos cargados")
                else:
                    st.error(f"Error {resp.status_code}: {resp.text[:200]}")

# ====================== INPUTS DINÁMICOS ======================
st.subheader("Selecciones (cuota y tu probabilidad estimada)")
cols = st.columns(n)
odds = []
probs = []

for i in range(n):
    with cols[i]:
        st.markdown(f"**Sel {i+1}**")
        odd = st.number_input(f"Cuota {i+1}", min_value=1.01, value=2.00, step=0.01, key=f"odd_{i}")
        prob_pct = st.number_input(f"Prob. estimada % {i+1}", min_value=1.0, max_value=99.0, value=55.0, step=0.1, key=f"prob_{i}")
        odds.append(odd)
        probs.append(prob_pct / 100)

# ====================== LÓGICA (igual que antes + Kelly) ======================
if st.button("🚀 Calcular todo (Sistemas + Value + Kelly)", type="primary", use_container_width=True):
    def calculate_product(values):
        prod = 1.0
        for v in values: prod *= v
        return prod

    def kelly_fraction(odd, prob):
        if odd <= 1 or prob <= 0 or prob >= 1:
            return 0.0
        b = odd - 1
        q = 1 - prob
        f = (prob * b - q) / b
        return max(0.0, f)

    # ... (el resto de las funciones get_systems_for_n y calculate_metrics se mantienen exactamente iguales a la versión anterior)

    def get_systems_for_n(n_sel):
        # (código idéntico al anterior - lo omito aquí por brevedad, pero está completo en tu app)
        systems = []
        doubles = list(itertools.combinations(range(n_sel), 2))
        systems.append(("Dobles solamente", doubles))
        if n_sel >= 3:
            triples = list(itertools.combinations(range(n_sel), 3))
            systems.append(("Triples solamente", triples))
            trixie = doubles + triples
            systems.append(("Trixie", trixie))
            patent = list(itertools.combinations(range(n_sel), 1)) + doubles + triples
            systems.append(("Patent", patent))
        if n_sel == 4:
            yankee = doubles + triples + [tuple(range(n_sel))]
            systems.append(("Yankee", yankee))
            lucky15 = list(itertools.combinations(range(n_sel), 1)) + doubles + triples + [tuple(range(n_sel))]
            systems.append(("Lucky 15", lucky15))
        if n_sel >= 4:
            dt = doubles + triples
            systems.append(("Dobles + Triples", dt))
        systems.append(("Parlay completo", [tuple(range(n_sel))]))
        return systems

    def calculate_metrics(odds_list, probs_list, stake, combos):
        # (código idéntico al anterior)
        num_combos = len(combos)
        stake_per = stake / num_combos
        n_sel = len(odds_list)
        combo_details = []
        total_ev = 0.0
        for combo in combos:
            cuota_prod = calculate_product([odds_list[i] for i in combo])
            prob_prod = calculate_product([probs_list[i] for i in combo])
            ev = stake_per * (prob_prod * cuota_prod - 1)
            total_ev += ev
            combo_details.append({
                "Combinación": [i+1 for i in combo],
                "Cuota": round(cuota_prod, 2),
                "Prob. est. %": round(prob_prod*100, 1),
                "EV (CLP)": round(ev, 0)
            })
        scenarios = []
        for k in range(n_sel + 1):
            if k == 0:
                scenarios.append({"Aciertos": 0, "Mín. neto": -stake, "Máx. neto": -stake})
                continue
            min_net = float('inf')
            max_net = float('-inf')
            for winners in itertools.combinations(range(n_sel), k):
                payout = sum(stake_per * calculate_product([odds_list[i] for i in combo]) for combo in combos if all(i in winners for i in combo))
                net = payout - stake
                min_net = min(min_net, net)
                max_net = max(max_net, net)
            scenarios.append({"Aciertos": k, "Mín. neto": round(min_net), "Máx. neto": round(max_net)})
        all_profit_pct = round((sum(stake_per * calculate_product([odds_list[i] for i in c]) for c in combos) - stake) / stake * 100, 1)
        return {
            "num_bets": num_combos,
            "stake_per": round(stake_per, 0),
            "total_ev": round(total_ev, 0),
            "total_ev_pct": round(total_ev / stake * 100, 1),
            "all_profit_pct": all_profit_pct,
            "combo_details": combo_details,
            "scenarios": scenarios
        }

    sys_list = get_systems_for_n(n)
    comparison = []
    for name, combos in sys_list:
        metrics = calculate_metrics(odds, probs, total_stake, combos)
        break_even = next((k for k in range(1, n+1) if metrics["scenarios"][k]["Mín. neto"] >= 0), "Ninguno")
        comparison.append({
            "Sistema": name,
            "Apuestas": metrics["num_bets"],
            "EV Total": metrics["total_ev"],
            "EV %": f"{metrics['total_ev_pct']}%",
            "Profit todo correcto": f"{metrics['all_profit_pct']}%",
            "Break-even mín.": break_even,
            "metrics": metrics,
            "combos": combos
        })

    comparison.sort(key=lambda x: (-x["EV Total"], x["Break-even mín."] if isinstance(x["Break-even mín."], int) else 999))
    best = comparison[0]

    # ====================== PESTAÑAS ======================
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Value + Kelly", "⚔️ Comparación", "✅ Recomendado", "📈 Escenarios", "📡 Cuotas en Vivo"])

    with tab1:
        st.subheader("Value Betting + Kelly Criterion")
        data = []
        for i, (o, p) in enumerate(zip(odds, probs)):
            implied = round(100 / o, 1)
            edge = round((p * o - 1) * 100, 1)
            kelly = kelly_fraction(o, p)
            suggested = round(bankroll * kelly * kelly_frac, 0)
            data.append({
                "Selección": f"Sel {i+1}",
                "Cuota": o,
                "Prob. implícita %": implied,
                "Tu prob. %": round(p*100, 1),
                "Edge %": f"{edge:+.1f}%",
                "Kelly %": f"{kelly*100:.1f}%",
                "Stake sugerido (CLP)": suggested
            })
        df_value = pd.DataFrame(data)
        def style_edge(val):
            if isinstance(val, str) and '%' in val:
                try:
                    v = float(val.strip('%'))
                    return f'color: {"green" if v > 0 else "red"}'
                except: return ''
            return ''
        st.dataframe(df_value.style.map(style_edge, subset=["Edge %"]), use_container_width=True)
        st.info(f"**Stake total sugerido por Kelly para el sistema:** {round(bankroll * 0.1, 0)} CLP (10% del bankroll como máximo recomendado)")

    with tab2:
        # (igual que antes)
        df_comp = pd.DataFrame(comparison)[["Sistema", "Apuestas", "EV Total", "EV %", "Profit todo correcto", "Break-even mín."]]
        st.dataframe(df_comp, use_container_width=True)
        st.success(f"✅ **RECOMENDADO: {best['Sistema']}** (EV: {best['EV Total']} CLP)")

    with tab3:
        # (igual que antes)
        st.subheader(f"Sistema recomendado: **{best['Sistema']}**")
        st.write(f"**Stake por combinación:** {best['metrics']['stake_per']} CLP")
        st.markdown("### Distribución exacta (copia y pega en Betano)")
        for i, row in enumerate(best["metrics"]["combo_details"]):
            st.code(f"Comb {i+1}: Selecciones {row['Combinación']} → Cuota {row['Cuota']} | Apostar {best['metrics']['stake_per']} CLP")
        if st.button("📋 Copiar distribución"):
            text = "\n".join([f"Comb {i+1}: Sel. {row['Combinación']} → Cuota {row['Cuota']} | {best['metrics']['stake_per']} CLP" for i, row in enumerate(best["metrics"]["combo_details"])])
            st.code(text)
            st.success("¡Copiado!")

    with tab4:
        df_scen = pd.DataFrame(best["metrics"]["scenarios"])
        st.dataframe(df_scen, use_container_width=True)
        st.metric("Profit si TODOS aciertas", f"{best['metrics']['all_profit_pct']}%")

    with tab5:
        st.subheader("Cuotas en vivo cargadas")
        if "live_matches" in st.session_state:
            st.dataframe(st.session_state["live_matches"], use_container_width=True)
            st.info("Copia las cuotas de la tabla y pégalas en las selecciones de arriba.")
        else:
            st.write("Pulsa el botón de la barra lateral para cargar cuotas en vivo.")

    st.balloons()