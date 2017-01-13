#!/usr/bin/env bash

while [[ $# -gt 1 ]]
do
    key="$1"
    case ${key} in
        -s|--start) START="$2";shift;;
        -e|--end) END="$2";shift;;
        *) ;;
    esac
    shift
done

counter=${START}

while [[ ${counter} -lt ${END} ]]
do
    echo "Parsing Folder Letters_$counter"
    #gsed -r -i "s/Letters_[0-9]+/Letters_${counter}/" config.json
    python main.py -d server --dir /home/research/ucrecruit/stem_letters/split/Letters_${counter}
	counter=$(( counter+1 ))
done
