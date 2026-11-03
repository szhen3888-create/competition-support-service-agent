-- 逻辑结构参考（SQLite / MySQL 通用语义）
-- 实际建表由 SQLAlchemy init_db() 完成

CREATE TABLE IF NOT EXISTS competitions (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(200) NOT NULL,
  level VARCHAR(50),
  category VARCHAR(80),
  major_tags VARCHAR(255),
  grade_range VARCHAR(80),
  tech_direction VARCHAR(120),
  organizer VARCHAR(120),
  year INTEGER,
  register_deadline DATE NULL,
  contest_date DATE NULL,
  location VARCHAR(120),
  fee FLOAT DEFAULT 0,
  award_setting TEXT,
  materials TEXT,
  description TEXT,
  status VARCHAR(30),
  created_at DATETIME
);

CREATE TABLE IF NOT EXISTS participations (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  competition_id INTEGER NOT NULL,
  year INTEGER,
  student_name VARCHAR(80),
  student_id VARCHAR(40),
  major VARCHAR(80),
  grade VARCHAR(40),
  team_name VARCHAR(120),
  instructor VARCHAR(80),
  project_title VARCHAR(200),
  award_level VARCHAR(40),
  award_rank VARCHAR(40),
  remark TEXT,
  created_at DATETIME,
  FOREIGN KEY (competition_id) REFERENCES competitions(id)
);

CREATE TABLE IF NOT EXISTS finance_drafts (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  kind VARCHAR(30),
  title VARCHAR(200),
  competition_name VARCHAR(200),
  payload_json TEXT,
  content_md TEXT,
  export_path VARCHAR(500),
  created_at DATETIME
);

CREATE TABLE IF NOT EXISTS workspace_drafts (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  kind VARCHAR(40),
  title VARCHAR(200),
  content_md TEXT,
  meta_json TEXT,
  export_path VARCHAR(500),
  created_at DATETIME
);
