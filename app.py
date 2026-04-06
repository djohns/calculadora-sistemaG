import streamlit as st
import itertools
import pandas as pd

st.set_page_config(page_title="Calculadora Sistemas + Value Betting", layout="wide")
st.title("🧮 Calculadora de Apuestas de Sistema + Value Betting")
st.markdown("**Versión web** – Usa tu probabilidad estimada real y encuentra el sistema más rentable")

# --- INPUTS EN SIDEBAR ---
with st.sidebar:
    st.header("📥 Datos de entrada")
    n = st.slider("Número de selecciones", min_value=3, max_value=8, value=4, step=1)
    total_stake = st.number_input("Monto total a invertir (CLP)", min_value=1000, value=100000, step=10000)
    st.caption("Cambia el número de selecciones y se actualizarán los campos")

# --- INPUTS DINÁMICOS ---
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

if st.button("🚀 Calcular todos los sistemas y Value Betting", type="primary", use_container_width=True):
    # --- LÓGICA (igual que antes pero optimizada para Streamlit) ---
    def calculate_product(values):
        prod = 1.0
        for v in values:
            prod *= v
        return prod

    def get_systems_for_n(n_sel):
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
        num_combos = len(combos)
        stake_per = stake / num_combos
        n_sel = len(odds_list)
        
        # Value Betting por combo
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
        
        # Escenarios
        scenarios = []
        for k in range(n_sel + 1):
            if k == 0:
                scenarios.append({"Aciertos": 0, "Mín. neto": -stake, "Máx. neto": -stake})
                continue
            min_net = float('inf')
            max_net = float('-inf')
            for winners in itertools.combinations(range(n_sel), k):
                payout = 0.0
                for combo in combos:
                    if all(i in winners for i in combo):
                        payout += stake_per * calculate_product([odds_list[i] for i in combo])
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
    
    # Ordenar por mejor EV y menor riesgo
    comparison.sort(key=lambda x: (-x["EV Total"], x["Break-even mín."] if isinstance(x["Break-even mín."], int) else 999))
    best = comparison[0]

    # --- MOSTRAR RESULTADOS ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Value en Singles", "⚔️ Comparación de Sistemas", "✅ Recomendado", "📈 Escenarios"])

    with tab1:
        st.subheader("Value Betting en selecciones individuales")
        data = []
        for i, (o, p) in enumerate(zip(odds, probs)):
            implied = round(100 / o, 1)
            edge = round((p * o - 1) * 100, 1)
            data.append({
                "Selección": f"Sel {i+1}",
                "Cuota": o,
                "Prob. implícita %": implied,
                "Tu prob. %": round(p*100, 1),
                "Edge %": f"{edge:+.1f}%"
            })
        df_value = pd.DataFrame(data)
        st.dataframe(df_value.style.apply(lambda x: ["color: green" if float(x["Edge %"][:-1]) > 0 else "color: red" for x in x], axis=1), use_container_width=True)

    with tab2:
        st.subheader("Comparación completa de sistemas")
        df_comp = pd.DataFrame(comparison)[["Sistema", "Apuestas", "EV Total", "EV %", "Profit todo correcto", "Break-even mín."]]
        st.dataframe(df_comp, use_container_width=True)
        st.success(f"✅ **RECOMENDADO: {best['Sistema']}** (EV: {best['EV Total']} CLP)")

    with tab3:
        st.subheader(f"Sistema recomendado: **{best['Sistema']}**")
        st.write(f"**Stake por combinación:** {best['metrics']['stake_per']} CLP")
        st.write(f"**Número de apuestas:** {best['metrics']['num_bets']}")
        
        st.markdown("### Distribución exacta (copia y pega en Betano)")
        for i, row in enumerate(best["metrics"]["combo_details"]):
            st.code(f"Comb {i+1}: Selecciones {row['Combinación']} → Cuota {row['Cuota']} | Apostar {best['metrics']['stake_per']} CLP")
        
        if st.button("📋 Copiar toda la distribución al portapapeles"):
            text = "\n".join([f"Comb {i+1}: Sel. {row['Combinación']} → Cuota {row['Cuota']} | {best['metrics']['stake_per']} CLP" for i, row in enumerate(best["metrics"]["combo_details"])])
            st.code(text)
            st.success("¡Copiado! Pégalo en Betano")

    with tab4:
        st.subheader("Escenarios según número de aciertos")
        df_scen = pd.DataFrame(best["metrics"]["scenarios"])
        st.dataframe(df_scen, use_container_width=True)
        st.metric("Profit si TODOS aciertas", f"{best['all_profit_pct']}%")

    st.balloons()