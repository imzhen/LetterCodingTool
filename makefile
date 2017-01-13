data_source=/home/research/ucrecruit/letter/original
data_split=/home/research/ucrecruit/letter/split
data_parsed=/home/research/ucrecruit/letter/parsed

clean:
	rm -rf data/fail/* data/results/* log/*

file_name_preprocess:
	find ${data_source} -name "*[ \'\(\)]*.*" -type f -print0 | while read -d $'\0' f; do mv -v "$f" "${f//[ \'\(\)]/}"; done

file_split:
	scripts/file_splitter.sh ${data_source} ${data_split}
