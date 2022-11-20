setlocal
set INC0="D:/wrk/clang-test/test/ICU/icu4c/include"
set INC1="C:/Program Files (x86)/Windows Kits/10/Include/10.0.19041.0/ucrt"
set INC2="C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.31.31103/include"

set DEF0="_MBCS"
set DEF1="WIN32"
set DEF2="_DEBUG"
set DEF3="WINVER=0x0601"
set DEF4="_WIN32_WINNT=0x0601"
set DEF5="_CRT_SECURE_NO_DEPRECATE"

set SRC="D:/wrk/clang-test/test/ICU/icu4c/source/samples/cal/cal.c"

::t7.py -I %INC0% -I %INC1% -I %INC2% -D%DEF0% -D%DEF1% -D%DEF2% -D%DEF3% -D%DEF4% -D%DEF5% %SRC%
::t7.py -I %INC0% -I %INC1% -I %INC2% -D %DEF4% --source_file %SRC%

..\scripts\t7.py --include %INC0% --include %INC1% --include %INC2% -D%DEF0% -D%DEF1% -D%DEF2% -D%DEF3% -D%DEF4% -D%DEF5% --source_file %SRC% --dependency_file apa.d