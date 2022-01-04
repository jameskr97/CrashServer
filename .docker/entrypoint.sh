#!/bin/bash
set -e

# check to see if this file is being run or sourced from another script
_is_sourced() {
	# https://unix.stackexchange.com/a/215279
	[ "${#FUNCNAME[@]}" -ge 2 ] \
		&& [ "${FUNCNAME[0]}" = '_is_sourced' ] \
		&& [ "${FUNCNAME[1]}" = 'source' ]
}

_main() {
	# If trying to run webapp...
	if [ "$*" = "python3 ./main.py" ]; then

		# Ensure we have rw to correct directories
		# Permissions only modified for the webapp, as only that requires write access
		# TODO: This assumes all symbols will be stored on the same system.
		# This is not true for all installations, due to CrashServer being pre-release,
		# is acceptable until a remote symbol storage system is implemented.
		[ -d "/storage" ] && {
			find /storage \! -user "$PUID" -exec chown "$PUID:$PGID" '{}' +
			chmod 755 /storage
		}
		[ -d "/logs" ] && {
			find /logs \! -user "$PUID" -exec chown "$PUID:$PGID" '{}' +
			chmod 755 /logs
		}
	fi

	exec gosu "$PUID:$PGID" "$@"
}

if ! _is_sourced; then
	_main "$@"
fi