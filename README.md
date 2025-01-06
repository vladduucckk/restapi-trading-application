
# Trading Strategies REST API

## Overview

This project provides a REST API for managing and simulating trading strategies. The API allows users to create, update, delete, and view their trading strategies. It supports user registration, authentication using JWT, and integrates with RabbitMQ for message handling and Redis for caching. The simulation endpoint enables users to test their trading strategies using historical data.

## Technologies Used

- **Flask** – Web framework for building the API.
- **SQLAlchemy** – ORM for managing the database.
- **JWT (JSON Web Tokens)** – For user authentication.
- **Redis** – For caching strategies.
- **RabbitMQ** – For message handling.
- **Marshmallow** – For data validation and serialization.
- **PostgreSQL** – Relational database for storing user and strategy data.

## Features

### User Authentication
- **Register** a new user with a username and password (passwords are securely hashed).
- **Login** a user to get a JWT token for secure access to other API endpoints.

### Strategy Management
- **Create** a new trading strategy with conditions for buying and selling.
- **Get** all strategies for the authenticated user.
- **Update** an existing strategy.
- **Delete** a strategy.

### Strategy Simulation
- **Simulate** a strategy based on historical data (e.g., stock prices), with outputs such as total trades, profit/loss, win rate, and maximum drawdown.

### Message Queue (RabbitMQ)
- Send updates to RabbitMQ whenever a strategy is created, updated, or deleted.

### Caching (Redis)
- Cache strategies for quick retrieval and avoid database overhead.

## API Endpoints

### User Registration and Authentication

#### `POST /auth/register`
Registers a new user.

**Request Body**:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response**:
```json
{
  "message": "User registered successfully"
}
```

#### `POST /auth/login`
Authenticates a user and returns a JWT token.

**Request Body**:
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response**:
```json
{
  "access_token": "your_jwt_token"
}
```

### Strategy Management

#### `POST /strategies`
Creates a new trading strategy.

**Headers**:
- `Authorization: Bearer <your_jwt_token>`

**Request Body**:
```json
{
  "name": "Strategy Name",
  "description": "Description of the strategy",
  "asset_type": "stock",
  "buy_conditions": {
    "indicator": "momentum",
    "threshold": 100.0
  },
  "sell_conditions": {
    "indicator": "momentum",
    "threshold": 50.0
  },
  "status": "active"
}
```

**Response**:
```json
{
  "message": "Strategy created successfully"
}
```

#### `GET /strategies`
Gets all strategies for the authenticated user.

**Headers**:
- `Authorization: Bearer <your_jwt_token>`

**Response**:
```json
[
  {
    "id": 1,
    "name": "Strategy Name",
    "description": "Description",
    "asset_type": "stock",
    "buy_conditions": {"indicator": "momentum", "threshold": 100.0},
    "sell_conditions": {"indicator": "momentum", "threshold": 50.0},
    "status": "active"
  }
]
```

#### `PUT /strategies/<id>`
Updates an existing strategy.

**Headers**:
- `Authorization: Bearer <your_jwt_token>`

**Request Body**:
```json
{
  "name": "Updated Strategy Name",
  "description": "Updated description",
  "asset_type": "stock",
  "buy_conditions": {
    "indicator": "momentum",
    "threshold": 120.0
  },
  "sell_conditions": {
    "indicator": "momentum",
    "threshold": 60.0
  },
  "status": "active"
}
```

**Response**:
```json
{
  "message": "Strategy updated successfully"
}
```

#### `DELETE /strategies/<id>`
Deletes an existing strategy.

**Headers**:
- `Authorization: Bearer <your_jwt_token>`

**Response**:
```json
{
  "message": "Strategy deleted successfully"
}
```

### Strategy Simulation

#### `POST /strategies/<id>/simulate`
Simulates the trading strategy based on historical data.

**Headers**:
- `Authorization: Bearer <your_jwt_token>`

**Request Body**:
```json
[
  {
    "date": "2025-01-01",
    "close": 100.0,
    "volume": 10
  },
  {
    "date": "2025-01-02",
    "close": 110.0,
    "volume": 5
  }
]
```

**Response**:
```json
{
  "strategy_id": 1,
  "total_trades": 2,
  "profit_loss": 500.0,
  "win_rate": 50.0,
  "max_drawdown": 10.0
}
```

## Setup and Running the Project

### Prerequisites

1. Install Python 3.8 or higher.
2. Install Docker (optional, for RabbitMQ and Redis).
3. Create a `.env` file in the root of the project with the following contents:

```env
DATABASE_URI=postgresql://<user>:<password>@localhost/<dbname>
JWT_SECRET_KEY=your_jwt_secret_key
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Can you create a database named strategies_db

```postgres terminal
CREATE DATABASE strategies_db;
```

### Running the Application

1. Start the database and message queue (RabbitMQ and Redis) if not using Docker.
2. Run the Flask application:

```bash
python main.py
```

3. The API will be available at `http://localhost:5001`.

### Testing the API

You can test the API using tools like **Postman** or **curl**. Don't forget to include the JWT token in the `Authorization` header for routes that require authentication.

## Conclusion

This API enables efficient management of trading strategies with capabilities for user management, strategy handling, and strategy simulation. It integrates with Redis for caching and RabbitMQ for message processing, ensuring fast and reliable performance.
