#!/bin/sh

# default version is FPHX2 + ROCv1 + Large interface board readout
version=7
#version=6

usage()
{
    name=`basename $0`
    echo 
    echo "Usage: $name [-v N] FILE"
    echo " where FILE is the pathname to the file you are converting"
    echo "Options:"
    echo "  -v  N    Run with unpacker version N"
    echo
    exit $1
}

for i in $*; do
    case "$1" in
        -h)
            usage 0
            ;;
        -v)
            shift
            version=$1
            echo "Using version $version"
            shift
	    ;;
	-n) shift
	    numbuffers=$1
	    echo "Processing $numbuffers buffers"
	    shift
            ;;
    esac
done


file=$1

if [ -z "$numbuffers" ]; then
    root.exe -l -b <<EOF
.L fphx_raw2root.C+
fphx_raw2root("$1",0,$version)
.q
EOF
else
    root.exe -l -b <<EOF
.L fphx_raw2root.C+
fphx_raw2root("$1",0,$version,$numbuffers)
.q
EOF
fi