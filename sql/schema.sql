CREATE DATABASE IF NOT EXISTS qrmenu
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE qrmenu;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(190) NOT NULL,
  avatar VARCHAR(255) NULL,
  password_hash VARCHAR(255) NOT NULL,
  global_role ENUM('developer', 'user') NOT NULL DEFAULT 'user',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_email (email)
);

CREATE TABLE restaurants (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(160) NOT NULL,
  slug VARCHAR(120) NOT NULL,
  description TEXT NULL,
  classic_info TEXT NULL,
  phone VARCHAR(50) NULL,
  email VARCHAR(190) NULL,
  address VARCHAR(255) NULL,
  logo VARCHAR(255) NULL,
  work_hours TEXT NULL,
  admin_contact VARCHAR(255) NULL,
  director_contact VARCHAR(255) NULL,
  opening_date DATE NULL,
  support_phone VARCHAR(50) NULL,
  support_email VARCHAR(190) NULL,
  map_2gis_url VARCHAR(500) NULL,
  map_2gis_embed_url VARCHAR(500) NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'KZT',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by INT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_restaurants_slug (slug),
  KEY idx_restaurants_active (is_active),
  CONSTRAINT fk_restaurants_created_by
    FOREIGN KEY (created_by) REFERENCES users(id)
    ON DELETE SET NULL
);

CREATE TABLE restaurant_users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  restaurant_id INT NOT NULL,
  user_id INT NOT NULL,
  role ENUM('restaurant_admin') NOT NULL DEFAULT 'restaurant_admin',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_restaurant_users_restaurant_user (restaurant_id, user_id),
  KEY idx_restaurant_users_user (user_id),
  CONSTRAINT fk_restaurant_users_restaurant
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_restaurant_users_user
    FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE
);

CREATE TABLE categories (
  id INT AUTO_INCREMENT PRIMARY KEY,
  restaurant_id INT NOT NULL,
  name VARCHAR(100) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_categories_restaurant_name (restaurant_id, name),
  KEY idx_categories_restaurant (restaurant_id),
  CONSTRAINT fk_categories_restaurant
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    ON DELETE CASCADE
);

CREATE TABLE menu (
  id INT AUTO_INCREMENT PRIMARY KEY,
  restaurant_id INT NOT NULL,
  category_id INT NULL,
  name VARCHAR(200) NOT NULL,
  description TEXT NULL,
  ingredients TEXT NULL,
  price INT NOT NULL,
  amount VARCHAR(50) NULL,
  image VARCHAR(255) NULL,
  is_available BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_menu_restaurant_name (restaurant_id, name),
  KEY idx_menu_restaurant (restaurant_id),
  KEY idx_menu_category (category_id),
  CONSTRAINT fk_menu_restaurant
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_menu_category
    FOREIGN KEY (category_id) REFERENCES categories(id)
    ON DELETE SET NULL
);

CREATE TABLE restaurant_settings (
  restaurant_id INT PRIMARY KEY,
  theme_color VARCHAR(20) NULL,
  language VARCHAR(10) NOT NULL DEFAULT 'ru',
  service_fee_percent DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_restaurant_settings_restaurant
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    ON DELETE CASCADE
);

CREATE TABLE restaurant_visit_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  restaurant_id INT NOT NULL,
  session_id VARCHAR(64) NOT NULL,
  page_path VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_visit_restaurant_created (restaurant_id, created_at),
  KEY idx_visit_session (session_id),
  CONSTRAINT fk_visit_events_restaurant
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    ON DELETE CASCADE
);

CREATE TABLE menu_cart_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  restaurant_id INT NOT NULL,
  menu_item_id INT NOT NULL,
  session_id VARCHAR(64) NOT NULL,
  quantity_delta INT NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_cart_events_restaurant_created (restaurant_id, created_at),
  KEY idx_cart_events_menu_item (menu_item_id),
  KEY idx_cart_events_session (session_id),
  CONSTRAINT fk_cart_events_restaurant
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_cart_events_menu_item
    FOREIGN KEY (menu_item_id) REFERENCES menu(id)
    ON DELETE CASCADE
);
