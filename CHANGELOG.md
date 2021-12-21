# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
## Changed
- Attachment content no longer included on every page by default. Content requested on view attempt via webapi endpoint.

## [0.3.4] - 2021-12-21
### Added
- Update Docker to use private env file added to .gitignore.

### Fixed
- Crash Report chart now shows the most recent 7-days instead of the first recorded 7 days.

## [0.3.3] - 2021-12-16
### Added
- Graph on homepage which shows crashes for each day of the past week
- Added favicon for web browsers and apple icon shortcut
- Decoded minidumps for versioned symbols now show the symbol's related version number on the crash detail page 

### Changed
- Use S3 compatible storage for attachments

## [0.3.2] - 2021-12-11
### Changed
- Crash Detail prismjs attachment presentation is larger, and syntax is updated
- Switched init to use flask app factory design
- Added Flask-DebugToolbar for request debug information

### Added
- Allowed cli.py to be run from cli
- Added Flask-Migrate to easily upgrade database
- Add `upload_ip` column to minidump table

### Removed
- Remove minidump upload limit

### Fixed
- Crash report page delete action, deletes correct minidump.
- Fix reading files with bad/invalid utf-8 characters.

## [0.3.1] - 2021-10-29
### Removed
- `charset-normalizer`: Switched to using BytesIO

### Fixed
- Fixed web minidump upload to work with zero attachments
- Fixed web crash list from showing all rows as "Processing"
- Fixed symbol lists not showing symbol count for all os's
- Fixed linux icon not showing in symbol list

## [0.3.0] - 2021-09-29
### Added
- Add support for uploading attachments. Any additional files to minidump will be added as a row in the Attachments table, and stored to disk
- Crash detail page has tabs for stacktrace, and uploaded attachments

### Fixed
- "Crashed Thread" tag on crash detail page, marks the thread the actually crashed instead of the first thread

### Changed
- `MinidumpTask` table removed, with relevant variables merged into `Minidump` table.


## [0.2.0.4] - 2021-09-25
### Added
- Added `.docker` folder, which defines a docker based development environment.
- Redis+RQ task queue to decode minidumps
- Added prism.js for code formatting (though feature is WIP)

### Changed
- Updated Crash Report page to look cleaner and show dump metadata or decode progress.
- Updated Crash Report page to have a slim view for mobile pages.

### Removed
- Huey as a task queue

### Fixed
- Fixed bug preventing from upload webpage from uploading minidumps

## [0.2.0.3] - 2021-09-19
### Fixed
- Flush symbol after stored in database to get "symbol_location" from project

### Changed
- Symbol "doesn't exist", and "already uploaded" log messages

## [0.2.0.2] - 2021-09-18
### Added
- More log messages on minidump processing
- `/logs/app.log` for application logs

### Fixed
- Dockerfile to download essential library `libcurl3-gnutls` for stackwalker


## [0.2.0.1] - 2021-09-07
### Added
- Module to get system specific information

### Changed
- Switched from python logging module to [loguru](https://github.com/Delgan/loguru)

## [0.2.0] - 2021-09-05
### Added
- Allow for deep linking via `#` in url on the settings page
- CLI commands for creating and deleting user accounts
- Notify user if there are no symbols uploaded when trying to upload a minidump
- gunicorn is run from a python application script instead of the command line
- gunicorn access logs are written to the /logs directory

### Changed
- Disallow empty version argument when uploading symbol for versioned project

### Removed
- Removed config for domain.

## [0.1.1-alpha] - 2021-09-02
### Added
- Show API keys at settings page for each project.
- Allow password to be changed when form is posted 
- Add more config information at settings page about tab
- Ensure all storage directories are created at program startup

### Fixed
- Upload page not allowing upload after a wrong file was previously uploaded

## [0.1.0-alpha] - 2021-09-01
### Added
- View recently uploaded symbols at `/crash-reports` endpoint
- View uploaded symbols by project at `/symbols` endpoint
- Upload minidumps via publicly-accessible `/upload` webpage
- Upload minidump via `/api/minidump/upload` endpoint, with minidump specific api-key
  - Minidump uploads are limited to 10 per hour, per remote ip-address
- Upload symbols via `/api/symbol/upload` endpoint, with symbol specific api-key
- Login system (no registration) for admins to be able to
  - Create projects
  - View project data
  - View system information
- Admin panel after login is mostly non-functioning, and is still a WIP at this release
- Asynchronously decode any uploaded minidump
- Only decode minidumps if symbol is available
