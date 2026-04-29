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
