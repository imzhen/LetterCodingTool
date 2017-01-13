#!/usr/bin/env bash
pdftohtml -xml $1.pdf >& /dev/null
sed -ie 's/\xa0//g;s/\&amp\;//g;' $1.xml >& /dev/null
if grep "This document is confidential which means that the applicant waived their rights to access this letter. \
Interfolio received this letter directly from the" $1.xml >& /dev/null ; then
    sed -ie '/<page number="1"/,/<\/page>/d' $1.xml
fi