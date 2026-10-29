# Ledgerly Transaction Workspace

Ledgerly is a React/Vite INR dashboard backed by a FastAPI transaction ledger and MongoDB Atlas. The frontend never connects directly to MongoDB.

## Project layout

```text
transaction-ledge/
├── backend/
│   ├── app/
│   ├── tests/
│   ├── .env.example
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── firebase.json
│   ├── .env.example
│   ├── .env.production.example
│   └── package.json
├── .gitignore
├── README.md
└── render.yaml
```

## Backend

Requirements: Python 3.12+ and a MongoDB Atlas replica-set deployment.

```powershell
cd backend
python -m venv ..\.venv
..\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000`.

Backend environment variables:

```env
MONGODB_URL=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=transaction_ledger
APP_ENV=development
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CURRENCY=INR
```

Keep the real file at `backend/.env`. It is ignored by Git.

Health check:

```text
GET /health
```

Run backend tests from the project root:

```powershell
..\.venv\Scripts\python.exe -m pytest backend\tests -v
```

Or from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -v
```

MongoDB transactions require Atlas or another replica-set deployment. Existing Decimal128 values are not automatically converted; confirm the unit of historical data before presenting it as INR.

## Frontend

The frontend is React + Vite + TypeScript + Tailwind CSS.

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

Local frontend environment:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

For production, copy `.env.production.example` to `.env.production` and replace the placeholder with the deployed Render backend URL:

```env
VITE_API_BASE_URL=https://<your-render-service>.onrender.com
```

Production build:

```powershell
npm run build
```

## Docker backend

Build from the repository root:

```powershell
docker build -f backend\Dockerfile backend -t ledgerly-api
```

Run without embedding credentials in the image:

```powershell
docker run --rm -p 8000:8000 `
  -e MONGODB_URL="mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority" `
  -e MONGODB_DATABASE="transaction_ledger" `
  -e FRONTEND_ORIGINS="http://localhost:5173" `
  -e CURRENCY="INR" `
  ledgerly-api
```

The image uses the Render-provided `PORT` value and defaults to `8000`.

## Render deployment

[render.yaml](./render.yaml) prepares a Docker web service with:

- `backend/Dockerfile`
- `backend` as the Docker build context
- `/health` as the health check
- `MONGODB_URL`, `MONGODB_DATABASE`, and `FRONTEND_ORIGINS` as runtime secrets/configuration

In Render, set:

```text
MONGODB_URL=<your Atlas URI>
MONGODB_DATABASE=transaction_ledger
FRONTEND_ORIGINS=https://<your-firebase-project>.web.app
CURRENCY=INR
```

Do not commit these values.

## Firebase Hosting

[frontend/firebase.json](./frontend/firebase.json) serves the Vite `dist/` directory and rewrites client-side routes to `index.html`.

After installing and authenticating the Firebase CLI:

```powershell
cd frontend
npm run build
firebase login
firebase use <your-firebase-project-id>
firebase deploy --only hosting
```

No Firebase project ID is committed because one was not supplied. Set `VITE_API_BASE_URL` to the Render URL before building.
