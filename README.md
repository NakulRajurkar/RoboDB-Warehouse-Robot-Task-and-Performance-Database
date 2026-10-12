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
## Project Structure

- `sql/` - Database schema, triggers, procedures, views, and seed data
- `queries/` - SQL task demonstrations
- `tests/` - Automated database tests
- `robodb.py` - Command-line interface
- `robodb.db` - Local SQLite database, if included

## Testing

Run the automated test suite with:

python -m pytest