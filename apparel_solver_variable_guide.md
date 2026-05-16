# Industrial Engineering Manual: Parameter Calibration for Apparel MRP Solvers

This document establishes the scientific, physical, and financial methodologies required to determine and calibrate the configuration parameters of an advanced 2D Area-Yield Total Cost of Operation (TCO) apparel cutting solver. 

An optimization model is only as accurate as the operational truth it simulates. Inaccurate parameters lead to mathematical optimization anomalies—resulting in physical table overflows, financial margin loss, or unexecutable floor instructions.

---

## 1. Geometric & Physical Parameters

These parameters define the hard physical boundaries of the cutting room floor and the nesting capability of the Computer-Aided Design (CAD) software.

### 1.1 `MAX_TABLE_LENGTH_CM`
* **Definition:** The maximum linear length available on the spreading table for a single marker paper layout.
* **Industrial Determination Method:** 1. Measure the total physical ironwork length of the table from the fabric roll holder/clamping system to the cutting end block.
  2. Subtract a **Safety Margin** (typically $30\text{ cm}$ to $50\text{ cm}$) to account for:
     * Spreading machine deceleration and acceleration zones.
     * Table end-clamps and weights.
     * Operator clearance space.
  3. If your cutting department uses an automated conveyorized cutting bed (e.g., Lectra, Gerber, Eastman), `MAX_TABLE_LENGTH_CM` is restricted by the maximum static window size of the continuous conveyor advance, or the physical constraints of the static spreading table feeding it.
* **Formula:**
  $$\text{MAX\_TABLE\_LENGTH\_CM} = \text{Length}_{\text{physical}} - \text{Margin}_{\text{safety}}$$

### 1.2 `FABRIC_WIDTH_CM`
* **Definition:** The usable cross-feed cutting width ($Y$-axis) of the specific fabric roll under optimization.
* **Industrial Determination Method:**
  1. Fabric rolls are never perfectly uniform. Unroll the first 3 meters of a sample roll from the batch.
  2. Measure the minimum width from edge to edge.
  3. Deduct the width of the **Selvedges** (Ourelas)—the manufactured edges of the fabric roll which often feature pinholes, structural distortion, or glue. Typically deduct $1.5\text{ cm}$ to $2.0\text{ cm}$ per side ($3\text{ cm}$ to $4\text{ cm}$ total).
  4. For **Tubular Fabrics** (Malha Tubular), measure the flat width and multiply by 2 to capture the total 2D area slice, noting that the fold lines must remain strictly parallel to the table rails.
* **Formula:**
  $$\text{FABRIC\_WIDTH\_CM} = \text{Width}_{\text{gross}} - (2 \times \text{Width}_{\text{selvedge}})$$

### 1.3 `NESTING_EFFICIENCY`
* **Definition:** The historical coefficient representing the ratio of raw material consumed by actual garment panels versus the discarded interstitial scrap fabric.
* **Industrial Determination Method:**
  1. Query your CAD nesting software database (e.g., Audaces, Optitex, Gerber) for the past 30 to 90 days of production runs.
  2. Extract the **Marker Efficiency Percentage** (Aproveitamento de Encaixe) across similar fabric types and reference styles.
  3. *Calibration Rule:* Do not use peak efficiency numbers achieved on long, high-volume markers. Use the **weighted historical average** categorized by fabric category:
     * Woven Commodity (Plain Weave): $0.84 - 0.88$ ($84\% - 88\%$)
     * High-Stretch Circular Knits: $0.82 - 0.86$ ($82\% - 86\%$)
     * Pattern-Matched (Plaids/Stripes): $0.70 - 0.78$ ($70\% - 78\%$)

---

## 2. Garment-Specific Dimensional Mapping

### 2.1 `AREA_PER_SIZE_CM2`
* **Definition:** The net geometric surface area (in square centimeters) required to construct one full garment of a specific size. This represents the sum of all nested pattern pieces (front, back, sleeves, collars, internal components).

```
   +-------------------------------------------------------+
   |  [Front]     [Back]      [Sleeve L]   [Sleeve R]      | <-- Net Area Sum
   |   (Area)  +  (Area)   +    (Area)   +   (Area)        |
   +-------------------------------------------------------+
   |============= INTERSTITIAL SCRAP AREA =================| <-- Nesting Efficiency
   +-------------------------------------------------------+
```

#### Method A: The CAD Database Extraction (Recommended)
1. Open the graded digital model file in your CAD pattern engine.
2. Select a target size (e.g., Size M).
3. Access the design summary or piece property matrix. Extract the **Net Area Property** (Área Líquida) for every piece inside the garment model group.
4. Ensure internal cutouts or open holes within a piece (like pocket openings or neck cutouts) are subtracted automatically by the CAD engine.
5. Sum these values to get the true net area for that size group.

#### Method B: The Physical Fabric Weight Derivation
If digital CAD geometries are unavailable, industrial engineers can calculate the net surface area using precise weight measurements and fabric specification metadata.

1. Cut a perfect $10\text{ cm} \times 10\text{ cm}$ ($100\text{ cm}^2$) test square of the relaxed fabric. Weigh it on a calibrated digital scale to verify the fabric's actual **Grammage** in grams per square meter ($\text{g/m}^2$).
2. Take a complete set of physical cut pieces for one full garment of a target size (e.g., Size G), freshly stamped from a zero-waste sample run.
3. Weigh the combined garment pieces on the scale to obtain the net garment weight in grams ($G_{\text{net}}$).
4. Apply the area conversion formula:
   $$\text{AREA\_PER\_SIZE\_CM2} = \left( \frac{G_{\text{net}}}{\text{Gramatura (g/m}^2\text{)}} \right) \times 10,000$$

---

## 3. Financial-Material Pegging Matrix

### 3.1 `COST_PER_SIZE`
* **Definition:** The literal monetary cost of the raw fabric embedded within a single full garment of a specific size. This sets the baseline financial units for the entire TCO objective function.
* **Industrial Determination Method:**
  1. Determine your **Raw Fabric Cost per Square Centimeter** based on purchase invoices.
  2. Compute the value of the net area, then multiply by a **Structural Wastage Cushion** ($1.00 + \text{End loss allowance}$) to account for fabric roll ends, splicing overlap, and inevitable defects.

#### If Fabric is Purchased by Weight (Kilograms):
$$\text{Cost per cm}^2 = \frac{\text{Price per Kg}}{\text{Gramatura (g/m}^2\text{)} \times 10}$$

#### If Fabric is Purchased by Length (Linear Meters):
$$\text{Cost per cm}^2 = \frac{\text{Price per Linear Meter}}{\text{Roll Gross Width (cm)} \times 100}$$

#### Final Calculation:
$$\text{COST\_PER\_SIZE}[s] = \text{AREA\_PER\_SIZE\_CM2}[s] \times \text{Cost per cm}^2 \times 1.03$$
*(Where $1.03$ injects a standard $3\%$ structural safety buffer).*

---

## 4. Operational & Labor Cost Parameters

These values must be calculated using standard industrial time-studies. They must be denominated in the same currency unit as the `COST_PER_SIZE` parameter.

### 4.1 `LAYER_SPREADING_COST`
* **Definition:** The total financial cost incurred by the factory when spreading one single ply of fabric across the table length.
* **Industrial Determination Method:**
  1. Conduct a time study over 10 production cycles to measure the average duration (in minutes) it takes a spreading team (or an automated machine) to complete one pass down the table ($T_{\text{layer}}$).
  2. Calculate the combined hourly labor rate of the spreading operators assigned to that table ($R_{\text{labor}}$), including social charges, benefits, and operational overhead.
  3. Add the machine depreciation cost per minute ($R_{\text{machine}}$) if using an automated system.
* **Formula:**
  $$\text{LAYER\_SPREADING\_COST} = \left( \frac{R_{\text{labor}} + R_{\text{machine}}}{60} \right) \times T_{\text{layer}}$$

### 4.2 `MARKER_FIXED_BASE_COST`
* **Definition:** The administrative, computational, and technical setup cost required to prepare and execute a unique marker layout file.
* **Industrial Determination Method:**
  1. Calculate the average time a CAD technician takes to prepare, grade, verify, and execute a nesting run for an order ($T_{\text{cad}}$). Multiplied by their fully-loaded hourly rate.
  2. Add the amortized software license cost per print job token ($C_{\text{license}}$).
  3. Add the physical handling time required for the cutting room team to clean the spreading table surface, adjust the machine clamps, and thread the initial headers ($T_{\text{setup}}$) multiplied by the table's hourly labor rate.
* **Formula:**
  $$\text{MARKER\_FIXED\_BASE\_COST} = \left( T_{\text{cad}} \times \text{CAD Hourly Rate} \right) + C_{\text{license}} + \left( T_{\text{setup}} \times \text{Spreading Hourly Rate} \right)$$

### 4.3 `MARKER_PAPER_COST_PER_CM`
* **Definition:** The direct material cost of the physical consumable plotter paper and ink used per linear centimeter of printed marker layout.
* **Industrial Determination Method:**
  1. Obtain the invoice cost of a standard plotter paper roll (e.g., $100\text{ meters}$ long, $1.8\text{ meters}$ wide).
  2. Divide the total roll price by its length in centimeters ($10,000\text{ cm}$).
  3. Add a $10\%$ markup to represent ink cartridge consumption costs based on historical consumption ratios.
* **Formula:**
  $$\text{MARKER\_PAPER\_COST\_PER\_CM} = \left( \frac{\text{Price of Paper Roll}}{\text{Length of Roll in cm}} \right) \times 1.10$$

---

## 5. Tactical Search Control Guardrails

### 5.1 `MAX_PATTERNS`
* **Definition:** The hard upper bound on the number of unique marker configurations allowed to be active concurrently per colorway run.
* **Industrial Determination Method:** * Driven strictly by **CAD throughput capacity** and **physical table downtime constraints**. 
  * If set to 1 or 2, fabric waste will skyrocket on highly skewed orders. If set to 5+, the CAD team will become a bottleneck, and the cutting room will suffer prolonged downtime swapping patterns.
  * *Industrial Best Practice:* Set to **3** for standard mixed orders; escalate to **4** only for large orders with extreme size asymmetry across more than 5 size categories.

### 5.2 `MAX_PLY_LIMIT`
* **Definition:** The maximum number of fabric layers that can be stacked on top of each other before execution.
* **Industrial Determination Method:**
  * Driven by two physical limitations: **Fabric Physics** and **Cutting Head Capacity**.
  1. Measure the physical vacuum-compressed or uncompressed height of the fabric per ply.
  2. Determine the maximum blade thickness capacity of your CNC cutting knife head (e.g., $5\text{ cm}$ or $7\text{ cm}$). The stack height must not exceed $80\%$ of this blade stroke capacity.
  3. **Fabric Distortion Constraint:** Certain slick materials (silks, microfibers, certain polyesters) will slide or fuse under high knife heat if stacked too high. Thick materials (fleece, heavy denim) have high friction and will cause blade deflection if stacked over a certain limit.
  * *Industrial Calibration:*
    * Heavy Denim / Twill: $40 - 60\text{ plies}$ max.
    * Standard Cotton Jersey / Interlock: $80 - 100\text{ plies}$ max.
    * Lightweight Synthetic Knits / Linings: $120 - 150\text{ plies}$ max.

### 5.3 `SOLVER_TIME_LIMIT_SECONDS`
* **Definition:** The structural timeout ceiling allocated for the CP-SAT engine to optimize before returning the best available feasible solution.
* **Industrial Determination Method:**
  * This is an operational trade-off between user-experience latency and mathematical optimization depth.
  * Because CP-SAT uses asynchronous multi-worker tree searches, it usually hits the global minimum (or comes within $1\%$ of it) inside the first 10 seconds for standard batches. The remaining time is spent mathematically proving optimality.
  * *Calibration Rule:* Set to **15.0 to 30.0 seconds** for live production use inside a warehouse dashboard application. This prevents backend thread starvation while allowing the engine to complete an exhaustive combinatorial search.

---

## 6. Substitution & Quality Guardrails

### 6.1 `SUBSTITUTION_ANNOYANCE_TAX`
* **Definition:** The financial penalty weight (the "Delta") applied to size substitution events. It prevents the solver from triggering trivial size downgrades unless there is a genuine operational cost justification.
* **Industrial Calibration Rule:** * Must be strictly greater than 0, but smaller than the average raw cost increment between consecutive sizes. 
  * If set too low (e.g., $R\$\ 0.10$), the solver will cross-contaminate sizes frequently just to shave a single centimeter off the marker length. If set too high (e.g., $R\$\ 50.00$), the solver will completely disable its own substitution capacity, choosing to overproduce heavy scrap rather than swap a size.
  * *Industrial Standard:* Set to exactly **R$ 2.00** (or equivalent currency units). This makes the swap expensive enough to be a defensive "last resort," but keeps it cheap enough to easily override a full layer cost if an entire spreading cycle can be saved.

### 6.2 `MAX_DOWNGRADE_TYPES_PER_COLOR` & `MAX_DOWNGRADES_PER_TYPE`
* **Definition:** Constraints limiting the variety and volume of size substitutions allowed per batch.
* **Industrial Determination Method:**
  * Dictated directly by **Quality Control (QC) Agreements** with the end-client or brand management.
  * In commercial apparel, a size downgrade (delivering a size G cut using a slightly larger size GG marker slice to meet demand) must be heavily constrained. 
  * *Calibration Standards:*
    * High-Luxury / Tailored Apparel: `MAX_DOWNGRADE_TYPES_PER_COLOR = 0` (Completely disabled).
    * Standard Menswear / Leisurewear: `MAX_DOWNGRADE_TYPES_PER_COLOR = 2`, `MAX_DOWNGRADES_PER_TYPE = 20` to `50` units max per batch. This allows flexible adjustments in high-volume, relaxed-fit garments while keeping shipment distributions within standard retail variance limits ($3\%-5\%$).
