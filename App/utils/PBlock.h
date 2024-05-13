#ifndef PBLOCK_H
#define PBLOCK_H

#include <vector>

#include "config.h"
#include "types.h"
#include "Transaction.h"
#include "Hash.h"

#include "salticidae/stream.h"


class PBlock {
 private:
  bool set; // true if the block is not the dummy block
  Hash prevHash;
  unsigned int size = 0; // number of non-dummy transactions
  Transaction transactions[MAX_NUM_TRANSACTIONS];
  unsigned int seqNumber = 0;

  std::string transactions2string();

 public:
  PBlock(); // retruns the genesis block
  PBlock(bool b); // retruns the genesis block if b=true; and the dummy block otherwise
  PBlock(Hash prevHash, unsigned int size, unsigned int seqNumber, Transaction transactions[MAX_NUM_TRANSACTIONS]); // creates an extension of 'block'

  bool extends(Hash h);
  Hash hash();

  bool isDummy(); // true if the block is not set
  unsigned int getSize();
  unsigned int getSeqNumber();
  Transaction *getTransactions();

  void serialize(salticidae::DataStream &data) const;
  void unserialize(salticidae::DataStream &data);

  std::string toString();
  std::string prettyPrint();

  bool operator==(const PBlock& s) const;
};

#endif
