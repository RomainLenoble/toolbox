# Sourced by compare_*.sh / save_reference.sh / run_test.sh.
#
# Resolves where a run's *live* outputs sit -- we compare those in place
# against the stored references (or against another run), no local copy.
#
# Needs $here and $case_name set by the caller. Provides:
#   rp_node    <run_id>          -> prints path to that run's NODE.001_01
#   rp_fa_grib <run_id> <fname>  -> prints path to an FA/GRIB output (rundir)
#   rp_netcdf  <run_id> <tag>    -> prints path to an XIOS netCDF output (newest match)
#
# Base dir is ${REPRO_RUN_BASE:-$HOME/relances}/<GROUP>/<run_id>; <GROUP>
# and <INIDATE> are read from that run's param_Eclis (the .runs/<run_id>/
# copy if present, else cases/<case_name>/launch/).

_rp_param_file() {  # <run_id>
    local pf="$here/.runs/$1/param_Eclis"
    [ -f "$pf" ] || pf="$here/cases/$case_name/launch/param_Eclis"
    printf '%s\n' "$pf"
}

_rp_var() {  # <run_id> <VARNAME>  -> value of the `^VARNAME=` line
    grep -E "^$2=" "$(_rp_param_file "$1")" 2>/dev/null | head -1 | cut -d= -f2 | tr -d '[:space:]'
}

_rp_run_src() {  # <run_id>
    local group; group="$(_rp_var "$1" GROUP)"; : "${group:=TEST_SUITE}"
    printf '%s\n' "${REPRO_RUN_BASE:-$HOME/relances}/$group/$1"
}

rp_node() {  # <run_id>
    printf '%s\n' "$(_rp_run_src "$1")/rundir/NODE.001_01"
}

rp_fa_grib() {  # <run_id> <fname>
    printf '%s\n' "$(_rp_run_src "$1")/rundir/$2"
}

rp_netcdf() {  # <run_id> <tag>
    local ini; ini="$(_rp_var "$1" INIDATE | tr -cd '0-9')"
    local dir; dir="$(_rp_run_src "$1")/iox_keep/$ini"
    local matches=( "$dir"/*_arpsfx_"$2"_*.nc )
    if [ -e "${matches[0]}" ]; then
        printf '%s\n' "${matches[$(( ${#matches[@]} - 1 ))]}"   # newest by name
    else
        printf '%s\n' "${matches[0]}"                            # non-existent glob; caller reports
    fi
}
