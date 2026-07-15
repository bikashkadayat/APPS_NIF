# NIF Leave Management System

A modern, role-based leave management system built with Django REST Framework (backend) and React + Vite (frontend). Supports role-based access for makers (apply for leave), checkers (review requests), and approvers (approve/reject).

## Features

- **Role-Based Access Control**: Separate interfaces for makers (apply for leave), checkers (review requests), and approvers (approve/reject).
- **Leave Management**: Apply, track, and manage leave requests with calendar view.
- **User Registration**: Self-registration with automatic maker role assignment.
- **Team Calendar**: Visual calendar to view approved leaves across the team.
- **Responsive Design**: Modern, professional UI that works on all devices.
- **JWT Authentication**: Secure token-based authentication.

## Tech Stack

- **Backend**: Django 4.x, Django REST Framework, Simple JWT, SQLite
- **Frontend**: React 18, Vite, Axios, React Router
- **Styling**: Custom CSS with CSS Variables
- **Deployment**: Ready for production with static file serving

## Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

For the Docker workflow you only need **Docker** and the **Docker Compose plugin** — Python and Node are not required on the host.

## Running with Docker (Recommended)

The fastest way to run the whole stack (PostgreSQL + Django backend + cron worker + React frontend) is Docker Compose.

### 1. Create the `.env` file

The compose stack refuses to start without secrets. Copy the template and fill in the required values:

```bash
cp .env.example .env
```

At minimum set these two in `.env`:

```bash
# Generate a random key (requires Docker already running):
#   docker run --rm python:3.10-slim python -c "import secrets; print(secrets.token_urlsafe(60))"
DJANGO_SECRET_KEY=<a-long-random-string>

# Any strong password for the local PostgreSQL container:
DATABASE_PASSWORD=<a-strong-password>
```

`.env` is gitignored — never commit real secrets.

### 2. Build and start

```bash
docker compose up -d --build
```

This starts four containers: `nif-db`, `nif-backend`, `nif-cron`, and `nif-frontend`. Database migrations and static file collection run automatically on backend startup.

### 3. Create an admin login

The stack does not seed users automatically. Create an initial admin account:

```bash
docker compose exec backend python manage.py seed_admin \
  --email admin@gmail.com --password admin123 --name "System Administrator"
```

You will be prompted to change this password on first login.

### 4. Access the application

| Service      | URL                              |
|--------------|----------------------------------|
| Frontend     | http://localhost:5173            |
| Backend API  | http://localhost:8001/api/v1/    |
| Admin panel  | http://localhost:8001/admin/     |
| PostgreSQL   | localhost:5434                   |

> Host ports are remapped to avoid collisions: backend is exposed on **8001** (not 8000) and PostgreSQL on **5434** (not 5432).

### Common commands

```bash
docker compose logs -f          # Tail logs from all services
docker compose logs -f backend  # Tail a single service
docker compose ps               # Show container status
docker compose restart backend  # Restart one service
docker compose down             # Stop and remove containers
docker compose down -v          # Stop and also wipe the database volume (full reset)
docker compose build --no-cache # Force a clean rebuild
```

For production deployment with HTTPS, use `docker-compose.prod.yml` — see `DOCKER.md` and `docs/DEPLOYMENT.md`.

## Project Structure

```
leave-system/
├── backend/                 # Django backend
│   ├── config/             # Django settings
│   ├── users/              # User management app
│   ├── leaves/             # Leave management app
│   ├── db.sqlite3          # SQLite database
│   └── requirements.txt    # Python dependencies
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   └── hooks/          # Custom React hooks
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite configuration
└── README.md              # This file
```

## Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

5. **Create superuser (optional)**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server**:
   ```bash
   python manage.py runserver
   ```

The backend will be available at `http://localhost:8000`

## Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173` (proxied to backend API)

## Running the Full Application

1. **Start backend** (in one terminal):
   ```bash
   cd backend
   source venv/bin/activate
   python manage.py runserver
   ```

2. **Start frontend** (in another terminal):
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access the application**:
   - Frontend: `http://localhost:5173`
   - Backend API: `http://localhost:8000/api/v1/`
   - Admin panel: `http://localhost:8000/admin/`

## User Roles

- **Maker**: Can apply for leave
- **Checker**: Can review pending leave requests
- **Approver**: Can approve/reject leave requests
- **Admin**: Full access to all features

## API Endpoints

### Authentication
- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/register/` - User registration
- `GET /api/v1/auth/user/` - Get current user info

### Leaves
- `GET /api/v1/leaves/` - List leaves (filtered by role)
- `POST /api/v1/leaves/` - Create leave request (makers only)
- `POST /api/v1/leaves/{id}/set_status/` - Update leave status (approvers only)
- `GET /api/v1/leaves/balance` - Get leave balances
- `GET /api/v1/leaves/calendar` - Get approved leaves for calendar

## Development

### Backend
- Run tests: `python manage.py test`
- Check code: `python manage.py check`
- Create migrations: `python manage.py makemigrations`

### Frontend
- Build for production: `npm run build`
- Preview production build: `npm run preview`
- Lint code: `npm run lint`

## Deployment

### Backend
1. Set `DEBUG = False` in `config/settings.py`
2. Configure production database (PostgreSQL recommended)
3. Set up static file serving
4. Use production WSGI server (gunicorn)

### Frontend
1. Build the app: `npm run build`
2. Serve the `dist/` folder with any static server
3. Configure API base URL for production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For questions or issues, please create an issue in the repository.