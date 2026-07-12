# IEEE Conference Paper Implementation Plan: Continuous Road Roughness (IRI) Estimation via Sim-to-Real Ground Truth

This document outlines the structured, step-by-step implementation plan for writing the 6–8 page IEEE Conference Paper inside `D:\Coding\Hackathon\GFG\ARM\ARM\nish_conf_paper\main_conf.tex`. It incorporates all user feedback from `parts_to_write.md` as well as the approved user review comments.

---

## Core Scientific Propositions & Refinements (Incorporating Approved User Comments)

1. **Sim-to-Real Ground Truth Acquisition & Specific Environment/Vehicle Selection:**
   - While BeamNG.tech offers a vast catalog of vehicles and terrains, we specifically utilized **3 distinct vehicles** representing major passenger suspension classes:
     - **Roamer:** Multi-Utility / Sports Utility Vehicle (MUV/SUV, stiff suspension profile)
     - **Sunburst2:** Mid-size Sedan (balanced suspension profile)
     - **Vivace:** Hatchback (soft-sprung passenger profile)
   - And **3 environments**, customized by injecting potholes and road anomalies to simulate real-world municipal infrastructure:
     - **East Coast USA:** Countryside and hilly roads
     - **West Coast USA:** Urban city arterials, highways, and expressways
     - **Automation Test Track:** Controlled circuit with varied surface types, used primarily to test and validate our model.

2. **Rigorous Related Work & Empirical Limitations:**
   - Contrast our Sim2Real approach against recent empirical studies that mount Class 1 laser profilometers alongside smartphones on a single test vehicle. Show that while empirical studies achieve high in-distribution correlation on their specific test vehicle and local road category, they fail to generalize across heterogeneous suspensions or unrepresented road terrains.

3. **Sensor Placement & Measurement Protocol:**
   - Detail the virtual sensor placement (`images/beamNG_sensor_placement.jpg`):
     - Dual downward-facing narrow-beam LiDAR sensors mounted at left and right wheel tracks ($\pm 0.85\,\text{m}$ lateral offset) measuring instantaneous elevation $h_L(t)$ and $h_R(t)$.
     - Virtual dashboard `AdvancedIMU` measuring 3-axis linear acceleration and angular velocity, re-mapped to physical smartphone axes.

4. **Full Mathematical Derivations:**
   - Include the complete mathematical formulation for the **Curvature-Adaptive Mesh Tessellation Correction** ($\kappa$, $\alpha$, profile blending).
   - Include the full state-space formulation of the **World Bank Golden Car Quarter-Car Model** ($\mathbf{A}, \mathbf{B}, \mathbf{C}_{\text{out}}, \mathbf{D}$, state vector $\mathbf{x} = [z_s, \dot{z}_s, z_u, \dot{z}_u]^T$, differential equations, slope input $z'(d)$, spatial-to-temporal conversion $t = d/v_{\text{sim}}$, and the integral equation for IRI).

5. **Engineering Defenses for Empirical Metrics & Crowdsourced Context:**
   - Provide rigorous physical and systems defenses for our $R^2 = 0.493$ and MAE = $1.642\,\text{m/km}$:
     - **System Polling Jitter & Realistic Data Noise:** During simulation data collection, computational thread contention caused our target $100\,\text{Hz}$ sampling rate to occasionally drop to $30\text{--}50\,\text{Hz}$, directly mirroring the real-world OS thread scheduling jitter on commercial smartphones.
     - **Cost-Scaling Trade-Off:** A $\$20$ consumer smartphone measuring cabin sprung-mass vibrations versus a $\$50,000\text{--}\$200,000$ Class 1 optical laser profilometer.
     - **Foundational Probe for Continuous Crowdsourced Monitoring:** Explain how this continuous IRI estimator serves as the edge-inference engine for a scalable, crowdsourced urban pavement monitoring network.

---

## Modular Writing Strategy for `main_conf.tex`

We write `D:\Coding\Hackathon\GFG\ARM\ARM\nish_conf_paper\main_conf.tex` sequentially across Levels 1 to 6.
