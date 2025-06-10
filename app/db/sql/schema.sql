-- SQL schema to create additional tables for recipe tracking and user auth

-- Users table for authentication and role-based access
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'staff',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Recipes table representing menu items
CREATE TABLE IF NOT EXISTS recipes (
    recipe_id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Mapping of ingredients to recipes
CREATE TABLE IF NOT EXISTS recipe_items (
    recipe_item_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(item_id),
    quantity REAL NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (recipe_id, item_id)
);

-- Record sales of menu items using the recipe definitions
CREATE TABLE IF NOT EXISTS sales_transactions (
    sale_id SERIAL PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(recipe_id),
    quantity INTEGER NOT NULL,
    user_id INTEGER REFERENCES users(user_id),
    sale_date TIMESTAMP DEFAULT NOW(),
    notes TEXT
);
