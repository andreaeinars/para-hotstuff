#ifndef USER_TYPES_H
#define USER_TYPES_H

typedef struct _hash_t
{
  unsigned char hash[SHA256_DIGEST_LENGTH];
  bool set;
} hash_t;

typedef struct _rdata_t
{
  hash_t proph;
  View propv;
  hash_t justh;
  View justv;
  Phase1 phase;
} rdata_t;

typedef struct _sign_t
{
  bool set;
  PID signer;
  unsigned char sign[SIGN_LEN];
} sign_t;

typedef struct _signs_t
{
  unsigned int size;
  sign_t signs[MAX_NUM_SIGNATURES];
} signs_t;

typedef struct _just_t
{
  bool set;
  rdata_t rdata;
  signs_t signs;
} just_t;


#endif
