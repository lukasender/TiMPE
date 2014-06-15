for file in `ls etc/mappings`;
do
    cat etc/mappings/$file
    echo ';'
done | bin/crash
