# CrashServer 💥

An implementation of an upstream collection server for the [Google Crashpad](https://chromium.googlesource.com/crashpad/crashpad/) crash handler. Intended to be as an all-in-one setup for small-to-medium projects who want to ability to:

- Store symbols and decode minidumps for separate projects
- View a list of recent crashes for any given project
- Allow for minidump upload from a public webpage

Built for open-source projects that use Google Crashpad, and want to host their own crash collection server.

## TODO
- API
  - [x] `/api/minidump/upload` Upload Minidumps for project under endpoint.
    - [ ] Handle `gzip` minidump upload
  - [x] `/api/synbol/upload` Upload Symbols for project under endpoint, secured by `api_key`
- Web
  - [ ] List of all symbols for project
  - [ ] Upload minidump (publicly)
  - [ ] Upload symbols (authenticated users only)
- Backend
  - [ ] Ensure minidump can be decoded before producing readable minidump
  - [ ] Support for symbols on development versions of the project
  - [ ] Auto-delete minidumps after a selected interval
  - [ ] Single project mode
  - [ ] Implement `sym-upload-v2` protocol
- Misc
  - [ ] Documentation Generation
  - [ ] CI and Tests