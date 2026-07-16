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
ai-dropout-prediction/

├── frontend/
├── backend/
├── ml/
├── database/
├── knowledge_base/
├── docs/
├── requirements.txt
└── README.md
```

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

- [ ] Design database schema
- [ ] Develop backend APIs
- [ ] Implement authentication
- [ ] Build frontend
- [ ] Train and evaluate the ML model
- [ ] Integrate the counseling assistant
- [ ] Build RAG knowledge base (document ingestion + pgvector)
- [ ] Develop faculty dashboard
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