# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added

- View recently uploaded symbols at `/crash-reports` endpoint
- View uploaded symbols by project at `/symbols` endpoint
- Upload minidumps via publicly-accessible `/upload` webpage
- Login system (no registration) for admins to be able to
  - Create projects
  - Access project api keys
  - Purge minidumps
  - Delete projects
  - Enable/disable `sym-upload-{v1,v2}` protocols
  - View other users
  - View system information
- Upload symbols via `/api/symbol/upload` endpoint
- Upload minidump via `/api/minidump/upload` endpoint
- Asynchronously decode any uploaded minidump
- Only decode minidumps if symbol is available
