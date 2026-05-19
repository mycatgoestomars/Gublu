# Gublu

**Emotionally Intelligent Habit Tracking and AI Journaling Application**

Final Year Project · BSc (Hons) Artificial Intelligence · University of Greenwich · 2026

Gublu is a full-stack AI web application that detects, tracks, and models maladaptive coping behaviours using a hybrid multi-model architecture. It combines transformer-based emotion detection, fuzzy logic distress scoring, machine learning behavioural prediction, and GPT-supported conversational journaling into a unified pipeline - going beyond passive self-tracking to deliver proactive, data-driven behavioural insight.

> **Supported behaviours:** Procrastination · Overspending · Social Isolation

---

## Results

| Metric | Value |
|---|---|
| XGBoost F1 Score (optimised) | **0.92** |
| XGBoost Recall | **100%** |
| XGBoost Accuracy | **84.6%** |
| Total Tests | **52** |
| Test Pass Rate | **100%** |
| PSO Fuzzy Boundary Optimisation | Validated (comparable MSE / MAE pre and post) |

---

## Features

| Feature | Description |
|---|---|
| Daily Check-in | Structured mood, energy, trigger, and behaviour logging via multiple choice |
| Journal Void | GPT-4.1 conversational journaling with rule-based fallback (works without API key) |
| Emotion Detection | Fine-tuned DistilBERT classifies journal text into emotion categories |
| Fuzzy Distress Scoring | Mamdani-style fuzzy inference converts emotion scores to distress labels |
| Risk Detection | Keyword and ML-based crisis message detection with safety response routing |
| Pattern Engine | Discovers correlations between mood, triggers, environment, and behaviour |
| Prediction Engine | Rule-based forecasts from accumulated check-in patterns |
| XGBoost Streak Predictor | ML model predicts streak-break probability with top contributing factors |
| Trigger Analysis | Identifies the most recurring trigger patterns across a user's history |
| Simulation Profiles | Three pre-built user personas for demonstration and testing |
| Dashboard | Streak counter, weekly mood chart, journal tone summary, My Why anchor |

---

## Project Structure

```
Gublu/                          Flask backend (Python)
  api.py                        Main API server, all endpoints
  Gublu.py                      Core processing pipeline
  GPT_Response_Generation.py    Chatbot response generation (GPT + fallback)
  memory_manager.py             JSON storage and journal helpers
  ml_streak_predictor.py        XGBoost training and prediction
  predict.py                    DistilBERT emotion classification wrapper
  emotion_correction.py         Score adjustment for negation and context
  Fuzzy_Logic.py                Mamdani fuzzy inference and PSO boundary tuning
  risk_model.py                 Crisis detection and safety routing
  pattern_engine.py             Mood-trigger-behaviour correlation discovery
  prediction_engine.py          Rule-based behavioural forecasting
  decision_engine.py            Selects most relevant insight for chatbot context
  reasoning_engine.py           Natural language explanations for detected patterns
  streak_system.py              Behaviour-specific success rules and streak logic
  chat_memory.py                Short-term in-memory chat context (last 5 exchanges)
  simulate_user_data.py         Deterministic simulated user profile generation
  emotion_model/                Fine-tuned DistilBERT weights

gublu-ui/                       Next.js frontend (React / TypeScript)
  app/page.tsx                  Dashboard
  app/chat/page.tsx             Journal Void chatbot
  app/checkin/page.tsx          Daily check-in form
  app/streaks/page.tsx          Streak calendar and history
  app/triggers/page.tsx         Trigger pattern analysis
  app/predictions/page.tsx      ML prediction and risk display
  app/simulations/page.tsx      Simulation profile loader
  app/globals.css               Global styles
```

---

## System Architecture

```
User Browser (localhost:3000)
        |
        |  HTTP fetch() calls
        v
Flask API (localhost:5000)
        |
        |--- Gublu.py               (full processing pipeline)
        |--- GPT_Response_Generation.py
        |--- memory_manager.py      (reads/writes gublu_memory.json)
        |--- ml_streak_predictor.py (XGBoost model)
        |--- emotion_model/         (DistilBERT weights)
```

The frontend never calls OpenAI directly. All GPT requests are routed through the Flask `/chat` endpoint. The OpenAI API key lives in `.env` on the backend only and is excluded from Git.

---

## AI Pipeline

Every journal message passes through the following chain in `Gublu.py`:

```
User message
    |
    v
1. Emotion Detection       DistilBERT classifies into sadness, joy, anger, fear, surprise
    |
    v
2. Emotion Correction      Adjusts scores for negation, distress keywords, context
    |
    v
3. Fuzzy Distress Scoring  Mamdani inference maps emotions to distress score (0.0 to 1.0)
    |
    v
4. Risk Detection          Keyword + ML scan for crisis language
    |
    v
5. Response Generation     GPT-4.1 (with full context prompt) or rule-based fallback
    |
    v
Saved to chat_log in gublu_memory.json with emotions, distress, summary, risk level
```

### Emotion Detection

A DistilBERT-base-uncased model fine-tuned on the Hugging Face DAIR.AI Emotion dataset, classifying into five categories: sadness, joy, anger, fear, surprise. Trained on Google Colab (3 epochs). Weights stored in `emotion_model/`.

### Fuzzy Distress Scoring

Corrected emotion scores feed into a Mamdani-style fuzzy inference system producing a continuous distress score between 0.0 and 1.0, labelled as low distress, moderate distress, or high distress. Particle Swarm Optimisation generates and validates alternative fuzzy boundary configurations against the default parameters.

PSO results:

| Metric | Before PSO | After PSO |
|---|---|---|
| MSE | 0.01569 | 0.01570 |
| MAE | 0.08602 | 0.08611 |
| Boundary params | (0.32, 0.52, 0.72) | (0.352, 0.491, 0.9) |

### Risk Detection

Messages are scanned by `risk_model.py` using direct phrase matching and ML toxicity scoring before any response is generated. High-risk inputs are routed to a pre-coded safety template directing the user to professional support. Gublu does not diagnose or provide any clinical assessment.

### GPT Conversational Response

The Journal Void chatbot constructs a prompt containing the user's current emotion state, distress label, check-in context, 7-day journal sentiment summary, and relevant behavioural insights. A scope guardrail prevents off-topic responses. The fallback system uses pattern and prediction engine outputs with natural language templates, meaning the app works fully without an OpenAI API key.

### XGBoost Streak-Break Predictor

Trains on historical check-in data once 20+ entries are available. Features include both check-in variables and 6 weekly journal sentiment features:

**Check-in features:** energy · mood · trigger type · time of day · environment · streak length · recent failure counts (3-day and 7-day windows) · problem type

**Journal sentiment features:**

| Feature | Description |
|---|---|
| weekly_journal_distress_avg | Average distress score across the past 7 days of journal entries |
| weekly_sadness_avg | Average sadness score for the week |
| weekly_fear_avg | Average fear score for the week |
| weekly_anger_avg | Average anger score for the week |
| weekly_distress_trend | Direction of change (positive = worsening) |
| journal_entry_count_week | Number of journal entries logged that week |

**Model performance (RandomizedSearchCV optimised):**

| Metric | Default | Optimised |
|---|---|---|
| Accuracy | 0.7692 | **0.8462** |
| Precision | 0.8333 | **0.8462** |
| Recall | 0.9091 | **1.0000** |
| F1 | 0.8696 | **0.9167** |
| ROC-AUC | 0.4545 | 0.4091 |

Top features by importance: `energy (0.256)` · `time_of_day (0.244)` · `failures_last_7 (0.126)`

Model versioning is handled via `CURRENT_MODEL_VERSION` in `ml_streak_predictor.py`. Incrementing this value safely invalidates and retrains the model when the feature vector changes.

---

## User Flows

### First-Time Onboarding
1. Visit `/` — redirected to `/onboarding`
2. Enter name, select behaviour focus (procrastination / overspending / isolation), write My Why
3. POST `/user/setup` creates the profile
4. Redirect to `/checkin`

### Daily Check-in
1. Visit `/` — gate check finds no check-in today, redirect to `/checkin`
2. Select mood, energy, trigger, environment, behaviour, time of day
3. POST `/checkin` saves the entry and updates streak
4. Redirect to `/chat` with a personalised starter message based on the check-in

### Journal Void (Chatbot)
1. Personalised starter message based on today's check-in
2. User types freely
3. Each message runs through the full AI pipeline server-side
4. Response returned via GPT or fallback
5. All exchanges saved to persistent `chat_log`
6. Chat history persists across page navigation via sessionStorage; clears on reset or simulation load

### Simulation / Demo
1. Navigate to `/simulations`
2. Select Nadia, Marcus, or Lala
3. Confirm — POST `/simulations/load`
4. Backend generates realistic check-ins and journal entries, trains the ML model
5. Redirect to dashboard showing the simulated user's data

---

## API Reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/user/setup` | POST | Create user profile with name, problem type, and My Why |
| `/checkin` | POST | Submit daily check-in data |
| `/checkin/status` | GET | Check whether today's check-in is complete |
| `/dashboard` | GET | Retrieve dashboard summary data |
| `/history` | GET | Retrieve historical check-in records |
| `/journal-summary` | GET | Return aggregated journal tone and emotion stats |
| `/chat` | POST | Process journal message and return chatbot response |
| `/predictions` | GET | Return XGBoost streak-break risk score and top factors |
| `/simulations/load` | POST | Load a preset simulation profile |
| `/reset` | POST | Clear all memory and ML model |

---

## Data Storage

All data is stored in `gublu_memory.json`. Example structure:

```json
{
  "username": "Marcus",
  "chosen_problem": "isolation",
  "my_why": "I don't want to feel so alone anymore.",
  "streak": {
    "current_days": 5,
    "start_date": "2026-04-25",
    "last_check_in": "2026-05-02",
    "status": "active"
  },
  "daily_checkins": [
    {
      "date": "2026-05-02",
      "problem": "isolation",
      "mood": "low",
      "energy": "low",
      "triggers": ["loneliness"],
      "environment": "alone",
      "behaviour": "avoided people",
      "time_of_day": "night",
      "streak_broken": false
    }
  ],
  "chat_log": [
    {
      "timestamp": "2026-05-02T14:30:00",
      "user_message": "I feel invisible today",
      "bot_reply": "That sounds really hard...",
      "summary": "High distress entry. Dominant emotion: sadness.",
      "emotions": { "sadness": 0.8, "fear": 0.2, "anger": 0.1, "joy": 0.05 },
      "distress_score": 0.82,
      "distress_label": "high distress",
      "risk_level": "low"
    }
  ]
}
```

> `gublu_memory.json` and `ml_models/` are excluded from Git via `.gitignore`. Do not commit them.

---

## Simulation Profiles

| Profile | Behaviour | Description |
|---|---|---|
| Nadia | Procrastination | Resilient — strong streak consistency (~80%), occasional slip on tired evenings, mostly positive moods |
| Marcus | Social Isolation | Struggling — frequent streak breaks (~40%), often low energy, high distress journal entries |
| Lala | Overspending | Recovering — mixed results (~60%), started poorly but improving, recent uptick in successful days |

Each profile generates a deterministic history using fixed random seeds, producing consistent results across multiple runs.

---

## Testing

52 tests · 100% pass rate

| Category | What Is Tested |
|---|---|
| Journal persistence | Entries save correctly with summary, emotions, and distress label |
| Journal summary generation | Rule-based summaries contain accurate emotion and distress data |
| Robotic phrase filtering | `filter_insight()` blocks system phrases, passes real insights |
| Weekly sentiment aggregation | 7-day rolling window returns all 6 journal sentiment feature columns |
| Simulation profiles | All 3 profiles generate valid entries with emotion scores |
| XGBoost training | Model trains with journal features, model version = 2 |
| ML prediction output | Returns `risk_score`, `risk_level`, and `top_factors` |
| Emotion prediction | Sadness, joy, and anger inputs classified correctly |
| Emotion correction | Negation reduces joy, distress keywords boost sadness |
| Fuzzy logic | Mixed emotions produce moderate distress; high sadness produces high distress |
| Risk detection | Crisis phrases flagged high; safe inputs flagged low |
| Streak logic | Success and failure conditions correct for all three behaviour types |
| API endpoints | All endpoints return correct status codes and valid response shapes |

**Run all tests:**
```bash
cd Gublu
python test_journal_ml.py
```

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- OpenAI API key (optional — the app works fully without one)

### Backend
```bash
cd Gublu
pip install -r requirements.txt
python api.py
```

### Frontend
```bash
cd gublu-ui
npm install
npm run dev
```

The frontend runs on `http://localhost:3000` and communicates with the Flask backend at `http://localhost:5000`.

### OpenAI API Key (optional)
Create a `.env` file in the `Gublu/` directory:
```
OPENAI_API_KEY=your_key_here
```

The app runs fully without this. If the key is absent or GPT fails, the fallback response system activates automatically.

### .gitignore
The following are excluded from version control and must not be committed:
```
.env
venv/
__pycache__/
ml_models/
gublu_memory.json
```

---

## Limitations

- Trained and evaluated on simulated data only. Real-world performance requires human trials and a larger dataset
- JSON file storage is not suitable for production. A proper database (PostgreSQL, SQLite) would be needed for concurrency, security, and scale
- ROC-AUC of 0.41 indicates the model struggles to rank low vs. high risk cases due to class imbalance in the simulated dataset
- No real user validation. Ecological validity is limited by the predefined persona approach
- No user authentication in the current prototype

---

## Future Work

- Real user trials with ethical clearance and longitudinal data collection
- Database backend (PostgreSQL) with user authentication
- Voice input with emotional tone recognition integrated into the Journal Void
- Wearable and sensor data integration (heart rate, activity, sleep) for richer context
- Expanded ML models and deep learning approaches for streak prediction
- Mobile-responsive design and potential mobile app deployment
- Journal history browsing UI and data export functionality
- More simulation profiles covering a wider range of behavioural patterns

---

## Academic Context

Submitted in partial fulfilment of the requirements for the degree of BSc (Hons) Computer Science (Artificial Intelligence) at the University of Greenwich, May 2026.

**Supervisors:** Dr Jia Wang · Dr Hai Huang

---

## Ethical Considerations

Gublu is a self-awareness and behavioural accountability tool. It is not a clinical or diagnostic system. All conversational responses are designed to be emotionally supportive without providing medical or therapeutic advice. High-risk inputs are routed to professional support resources rather than handled autonomously. The system is designed in accordance with the UK GDPR, the Data Protection Act 2018, the BCS Code of Conduct, and the ACM Code of Ethics.

---

*Built with Python, Flask, React, and a lot of care for people who are trying to do better.*
