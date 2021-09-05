# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2021-09-05
### Added
- Allow for deep linking via `#` in url on the settings page
- CLI commands for creating and deleting user accounts
- Notify user if there are no symbols uploaded when trying to upload a minidump
- gunicorn is run from a python application script instead of the command line
- gunicorn access logs are written to the /logs directory

### Changed
- Switched from python logging module to [loguru](https://github.com/Delgan/loguru)
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
