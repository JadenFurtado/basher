create database automation;

-- Create a template for conducting nuclei scans
CREATE TABLE nuclei_configuration (id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,github_nuclei_template_url VARCHAR(255) NOT NULL,application_url VARCHAR(255) NOT NULL);


