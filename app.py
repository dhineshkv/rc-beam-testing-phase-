import streamlit as st
import math
import numpy as np

# ----------------------------------------------------
# IS 456 τ_c TABLE (p_t vs fck)
# ----------------------------------------------------
tc_table = {
    20: [0.28, 0.32, 0.36, 0.40, 0.45],  # fck M20
    25: [0.29, 0.33, 0.37, 0.41, 0.46],  # M25
    30: [0.30, 0.34, 0.38, 0.42, 0.47],  # M30
    35: [0.31, 0.35, 0.39, 0.43, 0.48],  # M35
    40: [0.32, 0.36, 0.40, 0.44, 0.49]   # M40
}
pt_range = [0.15, 0.25, 0.50, 0.75, 1.0]

tc_max = { 20:2.8, 25:3.1, 30:3.5, 35:3.7, 40:4.0 }

def get_tc(pt, fck):
    """Linear interpolation of τc from IS456 table."""
    pt = max(pt, 0.15)
    pt = min(pt, 1.0)

    arr = tc_table[fck]
    return float(np.interp(pt, pt_range, arr))

# ----------------------------------------------------
# Self-weight
# ----------------------------------------------------
def self_weight_kN_per_m(b, D):
    density = 25  # kN/m³
    return density * (b/1000) * (D/1000)  # kN/m

# ----------------------------------------------------
# Main Capacity Function
# ----------------------------------------------------
def calculate(fck, fy, b, D, L, load_type,
              main_dia, main_count, stirrup_dia, spacing):

    cover = 25
    d = D - cover - stirrup_dia - main_dia/2

    if d <= 0:
        return None, "Invalid depth"

    # Steel areas
    Ast = (math.pi/4)*(main_dia**2)*main_count
    Asv = (math.pi/4)*(stirrup_dia**2)*2

    # Flexural
    xu = (0.87*fy*Ast)/(0.36*fck*b)
    xu_max = 0.48*d
    xu = min(xu, xu_max)

    Mu = 0.36*fck*b*xu*(d - 0.42*xu)  # Nmm
    Mu_lim = 0.138*fck*b*d*d
    Mu = min(Mu, Mu_lim)

    # Effective span (IS456)
    eff_span = min(L + d, L)  # approx

    # Convert M -> Load
    if load_type == "Point Load":
        W_flex = 4 * Mu / eff_span
    else:
        W_flex = 6 * Mu / eff_span

    # Shear calculations
    pt = 100*Ast/(b*d)
    tc = get_tc(pt, fck)
    tc_lim = tc_max[fck]

    # Shear force at critical section (d from face)
    V = W_flex/2  # approximate for both PL & 2PL

    # τv = V / (b*d)
    tau_v = V/(b*d)

    # Concrete shear
    Vc = tc * b * d
    Vs = 0.87*fy*Asv*d/spacing
    Vu = Vc + Vs

    W_shear = 2*Vu

    # Governing load
    Wu = min(W_flex, W_shear)

    # Add self-weight load reduction
    sw = self_weight_kN_per_m(b, D) * (L/1000)  # kN
    Wu_net = Wu/1000 - sw  # convert N->kN then subtract SW

    # Failure mode
    if W_flex < 0.9*W_shear:
        mode = "Flexural"
    elif W_shear < 0.9*W_flex:
        mode = "Shear"
    else:
        mode = "Combined"

    # Shear safety flags
    warnings = []
    if tau_v > tc_lim:
        warnings.append("τv exceeds τc,max → unsafe section.")
    if Wu_net <= 0:
        warnings.append("Beam fails under self weight!")

    return {
        "Wu_kN_gross": Wu/1000,
        "Wu_kN_net": Wu_net,
        "Mu_kNm": Mu/1e6,
        "Vu_kN": Vu/1000,
        "d_mm": d,
        "pt_percent": pt,
        "tau_v": tau_v,
        "tau_c": tc,
        "tau_c_max": tc_lim,
        "mode": mode,
        "warnings": warnings
    }, None

# ----------------------------------------------------
# Streamlit UI
# ----------------------------------------------------
st.title("🔧 RC Beam Capacity Calculator (IS-456 Accurate Version)")

fck = st.selectbox("Concrete Grade", [20,25,30,35,40])
fy = st.selectbox("Steel Grade", [415,500])

b = st.number_input("Beam Width b (mm)", 150, 1000, 230)
D = st.number_input("Overall Depth D (mm)", 200, 1000, 450)
L = st.number_input("Beam Length L (mm)", 500, 10000, 4000)

load_type = st.selectbox("Load Type", ["Point Load", "Two Point Load"])

main_dia = st.number_input("Main Bar Dia (mm)", 8, 32, 16)
main_count = st.number_input("No. of main bars", 1, 8, 2)

stirrup_dia = st.number_input("Stirrup Dia (mm)", 6, 12, 8)
spacing = st.number_input("Stirrup spacing (mm)", 80, 300, 150)

if st.button("Calculate"):
    result, err = calculate(fck, fy, b, D, L, load_type,
                            main_dia, main_count, stirrup_dia, spacing)

    if err:
        st.error(err)
    else:
        st.success(f"GROSS capacity: **{result['Wu_kN_gross']:.2f} kN**")
        st.success(f"NET capacity (after self weight): **{result['Wu_kN_net']:.2f} kN**")
        st.info(f"Failure Mode: **{result['mode']}**")

        st.write("### Details")
        st.write(f"- Flexural Capacity: {result['Mu_kNm']:.2f} kN·m")
        st.write(f"- Shear Capacity (Vu): {result['Vu_kN']:.2f} kN")
        st.write(f"- Effective depth d: {result['d_mm']:.1f} mm")
        st.write(f"- Steel ratio pₜ: {result['pt_percent']:.2f}%")
        st.write(f"- τv: {result['tau_v']:.3f} MPa")
        st.write(f"- τc: {result['tau_c']:.3f} MPa")
        st.write(f"- τc,max: {result['tau_c_max']:.2f} MPa")

        if result["warnings"]:
            st.error("⚠️ Safety Warnings:")
            for w in result["warnings"]:
                st.warning(w)
