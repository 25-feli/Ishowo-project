CREATE DATABASE prospects;
USE prospects;

CREATE TABLE prospects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50) UNIQUE NOT NULL,
    sector VARCHAR(100),
    city VARCHAR(100),
    business_type VARCHAR(50),
    score FLOAT DEFAULT 0,
    ai_justification TEXT,
    is_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
