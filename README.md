# E_store
E_store is a Django-powered e_commerce application created as a learning project to deepen understanding of web development using the Django framework.

# Features
-   Admin panel with secure access to manage products and orders
-   Add-to-cart system with size selection and inventory control
-   Email notification for customer
-	Fully responsive design using Bootstrap
-	Environment-specific settings for development and production
-   Demo admin credentials for testing: username: demo_admin, password: demo1234

# Tech Stack
-	Language: Python
-	Framework: Django
-	Database: SQLite (development), PostgreSQL (production)
-	Frontend: Bootstrap
-	Hosting: Render
-	Other Tools: WhiteNoise, Celery

# Installation Instructions
- Clone the repository:
git clone <repository-url>
cd store

- Create a virtual environment:
python -m venv venv
source venv/bin/activate  

- Install dependencies:
pip install -r requirements.txt

# Environment Variables
Ensure the following environment variables are set:
-	SECRET_KEY: Django's secret key.
-	DEBUG: Set to True for development, False for production.
-	DATABASE_URL: Connection string for the PostgreSQL database in production.
-	EMAIL_HOST_USER and EMAIL_HOST_PASSWORD: Credentials for the email backend.

