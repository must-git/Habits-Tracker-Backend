# Habits Tracker Backend

This is the backend API for the Habits Tracker application, built with Django and Django REST Framework.

## Prerequisites

- Python 3.8+
- MongoDB

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd Habits-Tracker-Backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Database Setup

1. Ensure MongoDB is running.

2. Create the database:
   ```bash
   python manage.py migrate
   ```

## Running the Server

Start the development server:

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`.
