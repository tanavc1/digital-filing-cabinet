# 🎬 ALSP Pipeline: The Perfect Demo Script

**Goal**: Record a flawless 5-10 minute end-to-end demo of the ALSP Diligence Pipeline.
**Audience**: Investors / Prospective Clients.
**Key Themes**: Speed, Precision, "Factory-Scale" Efficiency.

---

## 🛠️ Pre-Flight Check
1. **Kill everything**: Ensure no old servers are running (`killall python3`, `killall node`).
2. **Start Clean**: Run the launcher:
   ```bash
   chmod +x start_demo.sh
   ./start_demo.sh   # Waiting for "DEMO IS LIVE!"
   ```
3. **Open Browser**: Go to `http://localhost:3000`.
4. **Download Data**: Have `golden_demo_dataset.zip` ready on your Desktop.

---

## 🎥 Scene 1: The "Command Center" (Project Home)
**Action**: Land on the `/dashboard` page.
**Talk Track**:
> "Welcome to the Digital Filing Cabinet. This is our mission control for high-volume contract diligence."
> "You can see we have an active acquisition project here: 'Acme Corp Series B'."
> "Notice the real-time stats: Deadline approaching in 3 days, and our review factory is ready."

---

## 🎥 Scene 2: High-Velocity Intake
**Action**: Go to **Intake** (or Auto-Pass).
**Action**: Drag & Drop `golden_demo_dataset.zip` into the upload zone.
**Action**: Watch the 5 files appear.
**Action**: Select **Playbook: Customer Contracts**. Click **Analyze**.
**Talk Track**:
> "We're ingesting a mixed bag of documents—MSAs, Vendor Agreements, Amendments, and even some irrelevant Leases."
> "Instead of manual triage, our AI engine instantly classifies and routes them."

*(Wait ~30 seconds for processing. Mention key stats: "Processing at ~5 seconds per document.")*

---

## 🎥 Scene 3: The Review Factory
**Action**: Go to **Review Queue**.
**Observation**:
- **Point out**: The "MSA" is ready for review.
- **Point out**: The "Lease" (Outlier) is marked **Not Applicable** (demonstrating intelligence).
- **Point out**: The "Vendor Agreement" (High Risk) has a red badge.

**Talk Track**:
> "The engine just filtered out the noise. The Lease was auto-skipped. The clean MSA is queued."
> "But look at this Vendor Agreement—it's already flagged a critical risk."

---

## 🎥 Scene 4: Precision Review (The "Wow" Moment)
**Action**: Click "Vendor Agreement - RiskyBusiness" to open it.
**Action**: Show the **Split View**.
**Action**: Click the **Issues** tab on the right.
**Action**: Hover over the "Change of Control" issue.
**Visual**: See the highlight in the document on the left.
**Talk Track**:
> "Here's the magic. The AI didn't just 'summarize'—it found a needle in the haystack."
> "A 'Change of Control' termination clause. That's a deal-breaker."
> "I can verify the evidence right here in the text."

**Action**: Click **Complete Review**.

---

## 🎥 Scene 5: Delivery
**Action**: Go to **Export / Delivery**.
**Action**: Click **Download Clause Matrix**.
**Action**: Open the Excel file (if you have Excel) or just show the button.
**Talk Track**:
> "Finally, we generate the client deliverable: a perfect Clause Matrix, ready for the deal team."
> "From upload to insight in minutes, not days."

---

## 🏁 Cut!
**Post-Demo**: Stop the recording. Run `./start_demo.sh` again if you need a retake (it resets gracefully).
