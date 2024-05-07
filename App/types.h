#ifndef TYPES_H
#define TYPES_H

#include <stdint.h>

enum unit { tt };

typedef uint8_t HEADER;

#define HDR_NEWVIEW     0x00
#define HDR_PREPARE     0x01
#define HDR_PREPARE_LDR 0x02
#define HDR_PRECOMMIT   0x03
#define HDR_COMMIT      0x04

#define HDR_TRANSACTION 0x18
#define HDR_REPLY       0x19
#define HDR_START       0x20

#define HDR_NEWVIEW_CH     0x21
#define HDR_PREPARE_LDR_CH 0x22
#define HDR_PREPARE_CH     0x23

typedef uint8_t Phase1;

#define PH1_NEWVIEW   0x0
#define PH1_PREPARE   0x1
#define PH1_PRECOMMIT 0x2
#define PH1_COMMIT    0x3

typedef unsigned int PID; // process ids
typedef unsigned int CID; // client ids
typedef unsigned int TID; // transaction ids
typedef unsigned int PORT;
typedef unsigned int View;

#endif
