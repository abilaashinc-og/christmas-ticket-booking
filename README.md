# London Community Park – Christmas Ticket Booking System  
Coursework Project for COMP1430

This is a simple Flask-based web system for booking tickets for Christmas events at London Community Park.  
It includes a user login/registration system, ticket booking with validation rules, and an admin dashboard for managing users and admin accounts.

---

## 🎄 Features

### User features
- Register and log in
- View Christmas events
- Book tickets (adult/child counts, seat type)
- Upload adult photo for identification
- Validation rules:
  - Some events require at least **one adult**
  - Maximum tickets per booking
- Styled and responsive pages

### Admin features
- Log in with admin role
- View all users
- Edit user details and roles
- Delete users
- Create new admin accounts through a form
- Access control using custom `admin_required` decorator

---

## 🗃️ Technology Stack

- **Python 3**
- **Flask**
- **Flask-Login**
- **Flask-SQLAlchemy**
- **SQLite** (local database)
- **HTML + CSS** (custom UI, stored in `/templates` and `/static`)
- Runs inside **GitHub Codespaces**

---

## 📁 Project Structure


