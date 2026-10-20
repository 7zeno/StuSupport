# StuSupport

> **AI-Based Dropout Prediction and Counselling System**

A web application that predicts students at risk of dropping out using machine learning and provides personalized counseling to support early intervention and improve student retention.

## Overview

Student dropout is a significant challenge in higher education, leading to academic, financial, and social consequences for both students and institutions.

This project aims to identify students who may be at risk of dropping out by analyzing academic indicators such as CGPA, SGPA, attendance, semester backlogs, and fee payment status. A Random Forest classifier is trained on historical student data to estimate each student's dropout risk.

The application provides faculty with a dashboard to monitor at-risk students and intervene at an early stage. Students identified as high-risk can interact with a counseling assistant based on a Large Language Model (Qwen via Groq API), which offers personalized guidance and directs them to appropriate institutional support. The assistant uses Retrieval-Augmented Generation (RAG) to ground its responses in the institution's actual policies and support resources, rather than relying solely on the model's general knowledge.

---

## Features

- Predict student dropout risk using a Random Forest classifier
- Faculty dashboard for monitoring at-risk students
- Personalized counseling assistant
- Retrieval-Augmented Generation (RAG) for grounding counseling responses in institutional policies and resources
- Student profile and academic record management
- Risk categorization (Low, Medium, High)
- Secure authentication using JWT
- RESTful API built with FastAPI

---

## Methodology

### 1. Data Collection

Collect academic and administrative data such as CGPA, SGPA, attendance, semester backlogs, and fee payment status from a centralized PostgreSQL database.

The initial model is trained and validated using the public dataset from Martins et al. (2021), *"Early prediction of student's performance in higher education: a case study"* (see References), which provides labeled records of student academic and demographic indicators for dropout/academic-success prediction. The centralized PostgreSQL database is then used for live inference once the institution's own student records are integrated.

### 2. Data Preprocessing & Feature Engineering

Clean the dataset, handle missing values, encode categorical variables, and prepare relevant features for model training.

### 3. Model Training & Evaluation

Train a Random Forest classifier using historical student records and evaluate its performance using Accuracy, Precision, Recall, and F1-Score.

### 4. Risk Prediction

Generate a dropout probability for each student and classify them into Low, Medium, or High risk categories.

### 5. Intervention & Counseling

Display high-risk students on the faculty dashboard and provide personalized recommendations through the counseling assistant.

### 6. Knowledge Retrieval (RAG)

Institutional documents (academic policies, financial aid criteria, counseling and mental health resources) are chunked, embedded, and stored as vectors. When a student interacts with the counseling assistant, relevant chunks are retrieved and injected into the LLM prompt alongside the student's risk profile, ensuring responses are grounded in accurate, institution-specific information.

---

## Tech Stack

### Frontend

- React.js
- Tailwind CSS

### Backend

- FastAPI (Python)

### Database

- PostgreSQL
- pgvector (vector similarity search for RAG)

### Machine Learning

- scikit-learn (Random Forest Classifier)
- pandas
- NumPy

### AI Counselor

- Qwen (via Groq API)
- Retrieval-Augmented Generation (RAG) using sentence-transformers embeddings + pgvector

### Authentication

- JWT (JSON Web Tokens)

### ORM

- SQLAlchemy

### Hosting

- Render
- Railway

### Version Control

- Git
- GitHub

---

## Project Structure

```text
stusupport/
├── frontend/            React + Tailwind (Vite)
│   └── src/{pages,components,lib}
├── backend/             FastAPI app
│   ├── app/{routers,services}   auth, students, dashboard, counselor; risk, rag, embeddings
│   ├── seed.py          demo data + knowledge base ingest
│   └── tests/
├── ml/                  synthetic data generator, dataset loaders, training script
├── database/schema.sql  reference DDL (PostgreSQL + pgvector)
├── knowledge_base/      institutional documents for RAG (templates)
├── docs/
├── docker-compose.yml   local PostgreSQL + pgvector
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ with the pgvector extension (or Docker; or skip it and use the built-in SQLite fallback for a first run)

### 1. Install and train the model

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Demo model on synthetic data (no download needed)
python ml/train.py --source synthetic

# Or: the Martins et al. (2021) dataset — download data.csv from
# https://archive.ics.uci.edu/dataset/697 into ml/data/, then:
python ml/train.py --source uci --csv ml/data/data.csv
```

The UCI dataset has no attendance-percentage column, so a model trained on it uses CGPA, SGPA, backlogs and fee status only (mapping in `ml/data_sources.py`). Retrain on your institution's own records to use attendance.

### 2. Configure and start the backend

```bash
docker compose up -d                 # PostgreSQL + pgvector on :5432 (optional)
cp backend/.env.example backend/.env # set DATABASE_URL, JWT_SECRET, GROQ_API_KEY
cd backend
python seed.py                       # tables, demo users, 60 demo students, knowledge base ingest
uvicorn app.main:app --reload        # http://localhost:8000/docs
pytest -q                            # API tests on a throwaway SQLite DB
```

Without `DATABASE_URL` the API uses `backend/stusupport.db` (SQLite). Without `GROQ_API_KEY` the counselor still runs RAG but returns the retrieved policy excerpts instead of a generated reply.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173 (proxies /api to :8000)
```

For deployment (e.g. backend on Render/Railway, frontend as a static site), build with `VITE_API_URL=https://your-api.example.com npm run build` and add the frontend's URL to `CORS_ORIGINS` on the backend.

Demo logins (password `password123`): `faculty@stusupport.dev`, `admin@stusupport.dev`, `student.high@stusupport.dev`, `student.medium@stusupport.dev`, `student.low@stusupport.dev`.

### 4. Replace the knowledge base templates

Files in `knowledge_base/` are templates with `[[placeholders]]`. Fill in your institution's real offices, contacts, deadlines and amounts, then run `python seed.py --ingest-only`.

### API overview

| Method | Path | Who |
| --- | --- | --- |
| POST | `/api/auth/login` | all |
| GET | `/api/auth/me` | all |
| POST | `/api/auth/users` | admin |
| GET/POST | `/api/students` | faculty, admin |
| GET | `/api/students/{id}` | staff, or the student themself |
| PATCH/DELETE | `/api/students/{id}` | faculty, admin |
| PUT | `/api/students/{id}/records` | faculty, admin (adds/updates a semester and re-scores) |
| POST | `/api/students/{id}/predict` | faculty, admin |
| POST/PATCH | `/api/students/{id}/notes[/{note_id}]` | faculty, admin |
| GET | `/api/dashboard/summary` | faculty, admin |
| POST | `/api/predictions/run-all` | faculty, admin |
| GET | `/api/model` | faculty, admin |
| POST | `/api/counselor/chat`, GET `/api/counselor/history` | students |
| POST | `/api/admin/knowledge-base/ingest` | admin |

Risk bands: probability < 0.35 Low, < 0.65 Medium, otherwise High (configurable in `.env`).

---

## System Workflow

```text
Student Records
       │
       ▼
PostgreSQL Database
       │
       ▼
Data Preprocessing
       │
       ▼
Random Forest Classifier
       │
       ▼
Dropout Risk Prediction
       │
       ▼
Faculty Dashboard
       │
       ├──────────────┐
       ▼              ▼
Low/Medium Risk   High Risk
                       │
                       ▼
          Knowledge Base Retrieval (RAG)
                       │
                       ▼
            Counseling Assistant (Qwen)
```

---

## Roadmap

- [x] Design database schema
- [x] Develop backend APIs
- [x] Implement authentication
- [x] Build frontend
- [x] Train and evaluate the ML model
- [x] Integrate the counseling assistant
- [x] Build RAG knowledge base (document ingestion + pgvector)
- [x] Develop faculty dashboard
- [ ] Deploy the application
- [ ] Complete documentation

---

## References

1. Martins, M.V., Tolledo, D., Machado, J., Baptista, L.M.T., and Realinho, V. "Early Prediction of Student's Performance in Higher Education: A Case Study." *Trends and Applications in Information Systems and Technologies*, vol. 1, Advances in Intelligent Systems and Computing, Springer, 2021. DOI: [10.1007/978-3-030-72657-7_16](https://doi.org/10.1007/978-3-030-72657-7_16) *(dataset used for model training)*
2. Breiman, L. "Random Forests." *Machine Learning*, vol. 45, no. 1, pp. 5–32, 2001.
3. Aulck, L., Velagapudi, N., Blumenstock, J., and West, J. "Predicting Student Dropout in Higher Education." *arXiv preprint*, arXiv:1606.06364, 2016.
4. Goren, O., et al. "Early Prediction of Student Dropout in Higher Education." *Proceedings of the 17th International Conference on Educational Data Mining (EDM)*, 2024.
5. Putra, L. G. R., et al. "Student Dropout Prediction Using Random Forest and XGBoost Method." *INTENSIF: Jurnal Ilmiah Penelitian dan Penerapan Teknologi Sistem Informasi*, vol. 9, no. 1, 2025.

---

## License

This project is intended for academic and educational purposes.