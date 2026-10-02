# Campus Lost &amp; Found

A web application for reporting and recovering lost property on the MMU
Cyberjaya campus. Students post items they have lost or found, search the
listings, and claim an item by describing a detail the owner kept private.
Administrators moderate listings, review reports and manage user accounts.

**Live application:** https://negat1ve.pythonanywhere.com
**Repository:** https://github.com/Kisaragisayu/2620MiniIT-G13-lost-and-found-webapp

CSP1123 Mini IT Project — Trimester 2620 — Group G13

| Name | Student ID | Responsibility |
|---|---|---|
| Mustafo Yusupov | 253FC255BB | Frontend, page templates, deployment |
| Umaralmukhtar Khazhzhazh | 253FC255JT | Backend routes, database, authentication |
| Zhabay Temirlan | 253FC255RE | Admin panel, roles, moderation |

Supervisor: Mr Willie Poh Kaw Lik

---

## Features

**For students**

- Register with an MMU email address and a security question for recovery
- Post a lost or found item with a photo, category, location and date
- Search and filter listings by keyword, category and location
- Submit a claim by describing a hidden detail only the real owner would know
- Approve or reject claims on your own listings, and mark them resolved
- Report a listing to the administrators
- Edit your name and change your password from your profile
- Recover a forgotten password by answering your security question

**For administrators**

- Review all users, listings, claims and reports from one panel
- Remove listings and resolve reports
- Ban and unban accounts
- Promote and demote administrators (super administrators only)

---

## Built with

- Python 3.10
- Flask 3.1.3
- Flask-SQLAlchemy 3.1.1
- SQLite
- Jinja2 templates, hand-written CSS and JavaScript (no frontend framework)

---

## Installation

The project needs Python 3.10 or newer. Everything else installs from
`requirements.txt`.

**1. Open a terminal in the project folder**

```
cd 2620MiniIT-G13-lost-and-found-webapp
```

**2. Create a virtual environment**

Windows:

```
python -m venv venv
venv\Scripts\activate
```

macOS or Linux:

```
python3 -m venv venv
source venv/bin/activate
```

The prompt should now start with `(venv)`. If it does not, the environment
is not active and the next step will install into the system Python.

**3. Install the dependencies**

```
pip install -r requirements.txt
```

---

## Configuration

The application reads one environment variable, `SECRET_KEY`, which Flask
uses to sign session cookies. If it is not set, a development fallback is
used automatically, so no configuration is needed to run the project
locally.

For a deployment, set it to a long random value:

Windows:

```
set SECRET_KEY=your-random-value-here
```

macOS or Linux:

```
export SECRET_KEY=your-random-value-here
```

A suitable value can be generated with:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

Uploaded photos are written to `static/uploads/`, which is created on
startup if it does not exist. Uploads are limited to 2 MB and to PNG, JPG,
JPEG and GIF files.

---

## Running the application

```
python app.py
```

Then open http://127.0.0.1:5000 in a browser.

The database is created automatically on startup. This submission includes
`instance/lostfound.db` already populated with sample listings and accounts,
so the application has data to show immediately.

### Sample accounts

| Role | Email | Password |
|---|---|---|
| Super administrator | demo.admin@student.mmu.edu.my | demo.admin@student.mmu.edu.my |
| Student | demo.student@student.mmu.edu.my | Demo1234 |

---

## Starting from an empty database

To run the project without the supplied data, delete
`instance/lostfound.db` and start the application again — an empty database
is created in its place. Two helper scripts are included:

**Populate sample data**

```
python seed_data.py
```

**Grant administrator rights to an existing account**

```
python make_admin.py someone@student.mmu.edu.my
```

The account has to be registered through the website first; the script only
changes the role of an account that already exists.

---

## Project structure

```
2620MiniIT-G13-lost-and-found-webapp/
├── app.py                  Routes, request handling, application config
├── models.py               Database models: User, Item, Claim, Flag
├── make_admin.py           Grants admin rights to an existing account
├── seed_data.py            Fills the database with sample listings
├── requirements.txt        Python dependencies
├── instance/
│   └── lostfound.db        SQLite database (created on first run)
├── templates/
│   ├── base.html           Shared layout: navbar, flash messages, dialogs
│   ├── base-auth.html      Layout for the login and password pages
│   ├── index.html          Browse listings, with search and filters
│   ├── item-detail.html    One listing, its claims and the claim form
│   ├── post-item.html      Create and edit a listing
│   ├── profile.html        Listings, claims, account details, password
│   ├── admin.html          Admin panel: users, listings, claims, reports
│   ├── login.html
│   ├── register.html
│   ├── forgot-password.html
│   ├── reset-password.html
│   ├── 403.html
│   └── 404.html
└── static/
    ├── css/style.css       Styles shared by every page
    ├── images/             Campus background and MMU logos
    └── uploads/            Photos uploaded with listings
```

---

## Notes on the design

**Claims are verified by a hidden detail.** When a listing is created, the
author can record a detail that is never shown publicly. A claimant has to
describe it in their own words, and the author compares the two. This is
what stops a listing from being claimed by whoever sees it first.

**Two base templates rather than one.** Pages with the navigation bar
extend `base.html`; the login, registration and password pages extend
`base-auth.html`, which has the campus background and no navigation. Shared
styling lives in `static/css/style.css`, so a change to a button or a badge
applies everywhere at once.

**Confirmation dialogs are declarative.** Any form or link carrying a
`data-confirm` attribute asks before it goes through, handled by a single
listener in `base.html`. Destructive actions get a red confirmation button.

---

## Troubleshooting

**`No module named 'flask'`** — the virtual environment is not active.
Run `venv\Scripts\activate` on Windows or `source venv/bin/activate`
otherwise, then try again.

**`no such column`** — the database file predates a change to the models.
SQLAlchemy creates missing tables but does not alter existing ones. Delete
`instance/lostfound.db` and restart; the database will be rebuilt.

**Port 5000 already in use** — another copy of the application is still
running. Close it, or start this one on a different port with
`python app.py --port 5001`.
