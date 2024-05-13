#ifndef HASH_H
#define HASH_H

#include "config.h"
#include "types.h"
#include <openssl/sha.h>
#include <string>
#include "salticidae/stream.h"

class Hash {
 private:
  unsigned char hash[SHA256_DIGEST_LENGTH];
  bool set; // true if the hash is not the dummy hash

 public:
  Hash();
  Hash(bool b);
  Hash(unsigned char hash[SHA256_DIGEST_LENGTH]);
  Hash(bool b, unsigned char hash[SHA256_DIGEST_LENGTH]);
  Hash(salticidae::DataStream &data);

  void serialize(salticidae::DataStream &data) const;
  void unserialize(salticidae::DataStream &data);

  bool getSet();
  unsigned char* getHash();
  bool isDummy(); // true if the hash is not set
  bool isZero();

  std::string prettyPrint();
  std::string toString();

  bool operator==(const Hash& s) const;
  bool operator<(const Hash& s) const;
};


#endif
