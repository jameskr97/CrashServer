Processing Executables
======================

These files are the bread-and-butter of CrashServer:

- `minidump_stackwalker`: The original binary from google breakpad to process a minidump file
- `stackwalker`: Mozilla's modification to `minidump_stackwalker` which outputs data to process in a json file format, and provides more data
	- Available at: https://github.com/mozilla-services/minidump-stackwalk
- `dump_syms`: Mozilla's rewrite of google breakpad, which allows for dumping symbols from mac (DWARF), linux (ELF), or windows (PDB) debug files.
	- Available at: https://github.com/mozilla/dump_syms

