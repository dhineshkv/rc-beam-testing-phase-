import streamlit as st
import math

# --------- tau_c approx function ----------
def tau_c(pt, fck):
    """Approximate tau_c (MPa) – good for demonstration."""
    pt = max(pt, 0.1)
    return 0.62 * math.sqrt(fck) / (1 + 1.5 / pt)

# --------- Capacity Calculation ----------
def calculate_capacity(fck, fy, b, D, L, load_type,
                       main_dia, main_count, stirrup_dia, spacing):

    clear_cover = 25  # ✅ Fixed as per IS456 beam requirement

    # Effective depth calculation
    d = D - clear_cover - stirrup_dia - (main_dia / 2)
    if d <= 0:
        return None

    Ast = (math.pi / 4) * (main_dia ** 2) * main_count
    Asv = (math.pi / 4) * (stirrup_dia ** 2) * 2  # 2-leg stirrup

    # Flexural calculation
    xu = (0.87 * fy * Ast) / (0.36 * fck * b)
    xu_max = 0.48 * d
    xu = min(xu, xu_max)

    Mu = 0.36 * fck * b * xu * (d - 0.42 * xu)   # Nmm
    Mu_lim = 0.138 * fck * b * d * d
    Mu = min(Mu, Mu_lim)

    # Convert to load
    if load_type == "Point Load":
        Wu_flex = 4 * Mu / L    # N
    else:
        Wu_flex = 6 * Mu / L

    # Shear calculation
    pt_ratio = 100 * Ast / (b * d)
    tau = tau_c(pt_ratio, fck)
    Vc = tau * b * d
    Vs = 0.87 * fy * Asv * d / spacing
    Vu = Vc + Vs

    Wu_shear = 2 * Vu

    # Final governing load
    Wu = min(Wu_flex, Wu_shear)

    # Failure mode
    if Wu_flex < 0.9 * Wu_shear:
        mode = "Flexural"
    elif Wu_shear < 0.9 * Wu_flex:
        mode = "Shear"
    else:
        mode = "Combined"

    return Wu / 1000, mode, Mu / 1e6, Vu / 1000, d, pt_ratio


# ------------------- STREAMLIT UI -------------------

st.title("RC Beam Capacity Calculator (Simple Version)")

fck = st.selectbox("Concrete Grade (fck)", [20, 25, 30, 35, 40])
fy = st.selectbox("Steel Grade (fy)", [415, 500])

b = st.number_input("Beam Width b (mm)", value=230)
D = st.number_input("Overall Depth D (mm)", value=450)
L = st.number_input("Beam Length L (mm)", value=4000)  # ✅ Updated label

load_type = st.selectbox("Load Type", ["Point Load", "Two Point Load"])

main_dia = st.number_input("Main Bar Diameter (mm)", value=16)
main_count = st.number_input("Number of Main Bars", value=2)

stirrup_dia = st.number_input("Stirrup Diameter (mm)", value=8)
spacing = st.number_input("Stirrup Spacing (mm)", value=150)

if st.button("Calculate"):
    result = calculate_capacity(
        fck, fy, b, D, L, load_type,
        main_dia, main_count, stirrup_dia, spacing
    )

    if result:
        Wu, mode, Mu, Vu, d, pt = result

        st.success(f"Ultimate Bearing Capacity: **{Wu:.2f} kN**")
        st.info(f"Failure Mode: **{mode}**")

        st.write("---")
        st.write(f"**Flexural Capacity (Mᵤ):** {Mu:.2f} kN·m")
        st.write(f"**Shear Capacity (Vᵤ):** {Vu:.2f} kN")
        st.write(f"**Effective Depth (d):** {d:.2f} mm")
        st.write(f"**Steel Ratio (pₜ):** {pt:.2f}%")

    else:
        st.error("Invalid dimensions: Effective depth is negative!")
