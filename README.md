# 🏠 Hostel Management System

A web-based **Hostel Management System** built with **Python, Flask, HTML, CSS, and JSON**.
The project provides separate experiences for **students and administrators**, allowing hostel applications, student management, room management, payments, complaints, staff management, and application processing.

This project was developed as a **Software Engineering academic/portfolio project** to demonstrate backend development, frontend integration, authentication, CRUD operations, and role-based access control.

---

## 🚀 Live Demo

**Live Website:**
Add your Render URL here after deployment.

---

## ✨ Features

### 🎓 Student Portal

Students can:

* Register / submit a hostel application
* Log in to their account
* View their profile
* View room information
* Check payment status
* Submit complaints
* Track their hostel-related information
* Log out securely

### 🛠️ Admin Dashboard

Administrators can:

* View dashboard statistics
* Manage students
* Manage hostel rooms
* Manage payments
* View and process hostel applications
* Approve or reject applications
* Manage complaints
* Resolve complaints
* Manage hostel staff
* Update hostel settings
* Search hostel records
* Log out securely

---

## 🔐 Demo Admin Access

The Admin Dashboard is available for project evaluation and portfolio demonstration.

**Email:** `admin@uet.edu.pk`
**Password:** admin123

> This is a demo account created specifically to allow visitors and recruiters to explore the administrative side of the project.

---

## 🧑‍💻 Technology Stack

| Technology   | Purpose                   |
| ------------ | ------------------------- |
| Python       | Backend programming       |
| Flask        | Web framework             |
| HTML5        | Page structure            |
| CSS3         | Styling and responsive UI |
| JavaScript   | Frontend interactions     |
| JSON         | Demo data storage         |
| Gunicorn     | Production server         |
| Git & GitHub | Version control           |
| Render       | Deployment                |

---

## 🏗️ Project Structure

```text
HOSTEL/
│
├── backend.py
├── requirements.txt
├── Procfile
├── README.md
├── .env.example
├── .gitignore
│
├── data/
│   ├── activity.json
│   ├── applications.json
│   ├── complaints.json
│   ├── payments.json
│   ├── settings.json
│   ├── staff.json
│   ├── students.json
│   └── users.json
│
└── templates/
    ├── home.html
    ├── index.html
    ├── login.html
    ├── portal.html
    └── style.css
```

---

## 🔄 User Flow

### Student Experience

```text
Home
  ↓
Student Login
  ↓
Student Registration / Hostel Application
  ↓
Application Submitted
  ↓
Application Reviewed by Admin
  ↓
Student Portal
  ├── Profile
  ├── Room Information
  ├── Payments
  └── Complaints
  ↓
Logout
```

### Admin Experience

```text
Home
  ↓
Admin Login
  ↓
Admin Dashboard
  ├── Dashboard
  ├── Students
  ├── Rooms
  ├── Payments
  ├── Applications
  ├── Complaints
  ├── Staff
  └── Settings
  ↓
Logout
```

---

## 🔒 Security & Backend Improvements

The project includes several security and reliability improvements for deployment:

* Environment variables used for sensitive configuration
* Admin credentials are not hardcoded in the source code
* Role-based authorization for protected API endpoints
* Student access restricted to authenticated users
* Admin-only management operations
* Sensitive application information is not exposed through public status endpoints
* Secure session cookie configuration
* Basic security response headers
* Input validation and length limits
* Duplicate student registration validation
* Atomic JSON file updates
* Production configuration with `debug=False`
* Gunicorn used as the production server
* `.env` excluded from Git using `.gitignore`

---

## ⚙️ Run Locally

> **Note:** You do not need to install Python or Flask to use the live demo. The following steps are only for running the project locally.

Python **3.10+** is recommended.

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd uet-hostel-management-system
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment

**macOS / Linux:**

```bash
source .venv/bin/activate
```

**Windows:**

```bash
.venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file based on `.env.example`.

Set:

```text
ADMIN_EMAIL=admin@uet.edu.pk
ADMIN_PASSWORD=admin123
SECRET_KEY=your-secret-key
SESSION_COOKIE_SECURE=0
```

### 6. Run the application

```bash
python backend.py
```

Open the local URL shown by Flask in your browser.

---

## ☁️ Deployment

The project can be deployed on **Render**.

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
gunicorn backend:app
```

### Required Environment Variables

```text
ADMIN_EMAIL
ADMIN_PASSWORD
SECRET_KEY
SESSION_COOKIE_SECURE
```

For HTTPS deployment on Render:

```text
SESSION_COOKIE_SECURE=1
```

---

## 🗄️ Data Storage

This project currently uses **JSON files** for data storage.

This approach was selected to keep the project simple and suitable for an academic/portfolio demonstration.

For a production-level hostel management system, the project could be upgraded to a proper database such as:

* PostgreSQL
* MySQL
* SQLite

A production database would provide better scalability, concurrent access, data persistence, backups, and reliability.

> **Note:** On hosting platforms with ephemeral filesystems, changes made to JSON files may not persist permanently after certain redeployments or restarts. The current implementation is therefore intended primarily as a demonstration project.

---

## 🎯 Project Goals

The main goals of this project were to demonstrate:

* Flask backend development
* Frontend and backend integration
* REST-style API endpoints
* Authentication and sessions
* Role-based authorization
* CRUD operations
* Form handling and validation
* JSON-based data management
* Error handling
* Deployment preparation
* Git and GitHub workflow

---

## 📌 Future Improvements

Possible future improvements include:

* PostgreSQL database integration
* Password hashing with a dedicated authentication system
* Email notifications
* Student password reset
* Advanced room allocation
* Online payment integration
* Admin activity logs
* CSRF protection
* Rate limiting
* Better analytics and reporting
* Cloud-based persistent storage
* More advanced role management

---

## 👩‍💻 Author

**Aqsa Khursheed**

Software Engineering Student
UET Lahore

### Areas of Interest

* Web Development
* App Development
* UI/UX Design
* Database Systems
* Artificial Intelligence

---

## ⭐ Project Status

**Completed — Portfolio / Academic Demonstration Project**

The project demonstrates a complete basic hostel management workflow with separate **Student** and **Admin** experiences.

⭐ Note

This project uses fictional demo data and is intended for educational and portfolio purposes. It is not intended to represent an official UET hostel management system.
