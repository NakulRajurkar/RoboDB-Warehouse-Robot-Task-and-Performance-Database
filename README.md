# RoboDB - Warehouse Robot Task Database

## Project Overview
RoboDB is a SQL-based warehouse robot task management
system built using SQLite and Python.

## Features
- Robot and task management
- Task status tracking
- SQL triggers for task history
- Stored-procedure-style operations
- Task archiving
- Database views and reports
- Automated tests using pytest

## Technologies
- Python
- SQLite
- SQL
- Pytest

## Run the Project

Build the database:

python robodb.py build

Run the archive query:

python robodb.py run queries/06_archive.sql

Run the tests:

python -m pytest