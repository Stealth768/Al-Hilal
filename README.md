# Al-Hilal: Precision Lunar Astronomy & Visibility Engine

Al-Hilal is a production-grade calendar orchestration engine designed to resolve the systematic divergence between algorithmic lunar calculations (e.g., the Umm al-Qura calendar system) and human optical visibility vectors. 

Optimized for high-precision celestial monitoring at New Delhi coordinates, the engine ingests real-time spatial matrices, computes local sunset glare indices, and executes dynamic predictive models to determine regional crescent visibility.

---

## 🏗️ System Flow Architecture

```text
[User selects Year via UI] 
          │
          ▼
[Django View Layer] ────► [hijri-converter Math Engine] ──► Generates Base Lunar Dates
          │                                                         │
          ▼                                                         ▼
[Dynamic Validation Engine] ◄───────────────────────────────────────┘
  Checks Visibility Thresholds:
  ├── Lunar Age  < 15 Hours? ──► [FAIL] ──► Auto-Shift Holiday (+1 Day)
  └── Sky Lag    < 40 Mins?  ──► [FAIL] ──► Auto-Shift Holiday (+1 Day)
          │
          ├───► [PASS] ──► Retains Mathematical Base Date
          │
          ▼
[Context Pipeline Engine] ──► Generates Dynamic Map Vectors (MoonCalc / SunCalc API Links)
          │
          ▼
[Rendered UI Table Output] ──► Feeds Decoupled REST API Endpoints
