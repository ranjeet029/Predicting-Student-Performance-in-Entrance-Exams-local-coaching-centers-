CREATE DATABASE student_ai;

USE student_ai;

-- ===============================
-- STUDENTS TABLE
-- ===============================

CREATE TABLE students(
id INT AUTO_INCREMENT PRIMARY KEY,

name VARCHAR(100) NOT NULL,

student_id VARCHAR(50) UNIQUE NOT NULL,

email VARCHAR(100) UNIQUE NOT NULL,

password VARCHAR(255) NOT NULL,

gender VARCHAR(10),

mobile VARCHAR(15),

father_name VARCHAR(100),

address TEXT,

batch VARCHAR(50),

admission_date DATE,


dob DATE,

photo VARCHAR(255),

created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ===============================
-- MARKS TABLE
-- ===============================

CREATE TABLE marks(
id INT AUTO_INCREMENT PRIMARY KEY,

student_id VARCHAR(50) NOT NULL,

maths INT DEFAULT 0,
physics INT DEFAULT 0,
chemistry INT DEFAULT 0,
biology INT DEFAULT 0,

attendance INT DEFAULT 0,
practice INT DEFAULT 0,

total INT DEFAULT 0,
rank_no INT DEFAULT 0,

FOREIGN KEY (student_id)
REFERENCES students(student_id)
ON DELETE CASCADE
ON UPDATE CASCADE
);


-- ===============================
-- ADMIN TABLE
-- ===============================

CREATE TABLE admin(

username VARCHAR(50) UNIQUE NOT NULL,

password VARCHAR(255) NOT NULL

);


-- ===============================
-- DATASET TABLE
-- ===============================

CREATE TABLE dataset(
id INT AUTO_INCREMENT PRIMARY KEY,

file_name VARCHAR(255) NOT NULL,

upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



-- ===============================
-- Courses TABLE
-- ===============================

CREATE TABLE courses (
id INT AUTO_INCREMENT PRIMARY KEY,
course_name VARCHAR(100),
duration VARCHAR(50),
fees DECIMAL(10,2),
description TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ===============================
-- management
-- ===============================

CREATE TABLE management_auth (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100),
    password VARCHAR(255)
);

CREATE TABLE sliders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    image VARCHAR(255)
);

CREATE TABLE courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100),
    description TEXT,
    faculty VARCHAR(100),
    duration VARCHAR(50),
    image VARCHAR(255)
);


CREATE TABLE exam_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100),
    tags VARCHAR(255),
    image VARCHAR(255)
);