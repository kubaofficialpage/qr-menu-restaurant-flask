USE qrmenu;

ALTER TABLE restaurants
  ADD COLUMN classic_info TEXT NULL AFTER description,
  ADD COLUMN email VARCHAR(190) NULL AFTER phone,
  ADD COLUMN work_hours TEXT NULL AFTER logo,
  ADD COLUMN admin_contact VARCHAR(255) NULL AFTER work_hours,
  ADD COLUMN director_contact VARCHAR(255) NULL AFTER admin_contact,
  ADD COLUMN opening_date DATE NULL AFTER director_contact,
  ADD COLUMN support_phone VARCHAR(50) NULL AFTER opening_date,
  ADD COLUMN support_email VARCHAR(190) NULL AFTER support_phone,
  ADD COLUMN map_2gis_url VARCHAR(500) NULL AFTER support_email,
  ADD COLUMN map_2gis_embed_url VARCHAR(500) NULL AFTER map_2gis_url;
