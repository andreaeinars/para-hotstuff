#ifndef CONFIG_H
#define CONFIG_H

#include "params.h"

// debug switches
#define DEBUG   true
#define DEBUG0  true
#define DEBUG1  true
#define DEBUG2  true
// to print timing info
#define DEBUGT  false
// adds ocalls to profile crypto in enclaves
#define DEBUGOT true
// to print 'EXECUTE' messages
#define DEBUGE  true
// to print client messages
#define DEBUGC  true

#define NO_SOCKET          -1
#define CONF_FILE_SIZE     250
#define MAXLINE            256
#define RSA_NUM_BITS4k     4096
#define RSA_NUM_BITS2k     2048
#define MAX_SIZE_PAYLOAD   4096 // TODO: change that to something sensible

// ----------------------------------------
// Colors
// ------

#define KNRM  "\x1B[0m"

// default background & different foreground colors
#define KRED  "\x1B[49m\x1B[31m"
#define KGRN  "\x1B[49m\x1B[32m"
#define KYEL  "\x1B[49m\x1B[33m"
#define KBLU  "\x1B[49m\x1B[34m"
#define KMAG  "\x1B[49m\x1B[35m"
#define KCYN  "\x1B[49m\x1B[36m"
#define KWHT  "\x1B[49m\x1B[37m"

// default background & different (light) foreground colors
#define KLRED  "\x1B[49m\x1B[91m"
#define KLGRN  "\x1B[49m\x1B[92m"
#define KLYEL  "\x1B[49m\x1B[93m"
#define KLBLU  "\x1B[49m\x1B[94m"
#define KLMAG  "\x1B[49m\x1B[95m"
#define KLCYN  "\x1B[49m\x1B[96m"
#define KLWHT  "\x1B[49m\x1B[97m"

// diferent background colors & white foreground
#define KBRED  "\x1B[41m\x1B[37m"
#define KBGRN  "\x1B[42m\x1B[37m"
#define KBYEL  "\x1B[43m\x1B[37m"
#define KBBLU  "\x1B[44m\x1B[37m"
#define KBMAG  "\x1B[45m\x1B[37m"
#define KBCYN  "\x1B[46m\x1B[37m"
#define KBWHT  "\x1B[47m\x1B[30m"


// #define KNRM  ""

// // default background & different foreground colors
// #define KRED  ""
// #define KGRN  ""
// #define KYEL  ""
// #define KBLU  ""
// #define KMAG  ""
// #define KCYN  ""
// #define KWHT  ""

// // default background & different (light) foreground colors
// #define KLGRN  ""
// #define KLRED  ""
// #define KLYEL  ""
// #define KLBLU  ""
// #define KLMAG  ""
// #define KLCYN  ""
// #define KLWHT  ""

// // diferent background colors & white foreground
// #define KBRED  ""
// #define KBGRN  ""
// #define KBYEL  ""
// #define KBBLU  ""
// #define KBMAG  ""
// #define KBCYN  ""
// #define KBWHT  ""

#endif
