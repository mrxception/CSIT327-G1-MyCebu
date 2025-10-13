# MyCebu
The MyCebu is a project that aims to develop a centralized, citizen-focused digital platform that enhances the accessibility, transparency, and efficiency of local government services in Cebu City. This initiative seeks to address existing challenges such as fragmented information systems, bureaucratic delays, and limited public access to essential services. By consolidating government ordinances, service directories, and public advisories into a single platform supported by an AI-powered assistant, the project endeavors to streamline government processes, improve citizen engagement, and foster greater public trust in local governance.

---

## Technology Stack

### Backend
- **Framework**: Django 5.2.6+ (Pure Django - templates, views, models)
- **Database**: Supabase 

### Frontend
- **Templates**: Django Template Language (DTL)
- **Styling**: TailwindCSS and Vanilla CSS for hybrid responsive design and styling catering developer preferences
- **Interactivity**: Minimal JavaScript with Django integration

---

## Setup & Run

### 1) Clone the repo

```bash
git clone https://github.com/mrxception/CSIT327-G1-MyCebu.git
cd CSIT327-G1-MyCebu
```

### 2) Create a virtual environment

**Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3) Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Create a `.env` file in the project root

> This project uses **Supabase** as its database and authentication provider.
> You’ll need your own **Supabase URL** and **anon public key** from your Supabase project.

```env
SUPABASE_URL=your-supabase-url-here
SUPABASE_KEY=your-supabase-anon-key-here
```

#### 🧭 How to get your Supabase keys:

1. Go to **[https://supabase.com](https://supabase.com)** and log in (or sign up).
2. Create a new project (or open an existing one).
3. In your Supabase dashboard, go to **Project Settings → API**.
4. Copy:

   * **Project URL** → paste into `SUPABASE_URL`
   * **anon public key** (under *Project API keys*) → paste into `SUPABASE_KEY`
5. Save the `.env` file — do **not** commit it to Git.

### 5) Apply migrations and run

```bash
python manage.py migrate
python manage.py runserver
```

Then open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser 🎉

### Deployment checklist (quick)

* Set `DEBUG=False`
* Set `ALLOWED_HOSTS` to your domain(s)
* Provide production `SECRET_KEY`
* Set a production `DATABASE_URL` (e.g., Supabase)
* Configure static files (e.g., `collectstatic`) according to your hosting provider’s guide

---

## Team Members

| Name                              | Role               | CIT-U Email                            |
| :-------------------------------- | :-----------------:| --------------------------------------:|
| Edralyn Rose Bibera               | Product Owner      | edralynrose.bibera                     |
| Rod Gabrielle Canete              | Business Analyst   | rodgabrielle.canete@cit.edu            |
| Ronel Atillo                      | Scrum Master       | ronel.atillo@cit.edu                   |
| Jay Yan Tiongzon                  | Lead Developer     | jayyan.tiongzon@cit.edu                |
| Franz Raven Sanchez               | Frontend Developer | franzraven.sanchez@cit.edu             |
| James Michael Siton               | Frontend Developer | jamesmichael.siton@cit.edu             |

---

## Deployed Link

(https://mycebu.onrender.com/)
