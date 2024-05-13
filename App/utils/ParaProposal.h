#ifndef PARA_PROPOSAL_H
#define PARA_PROPOSAL_H


#include "config.h"
#include "types.h"
#include "Just.h"
#include "PBlock.h"

#include "salticidae/stream.h"


class ParaProposal {
 private:
  Just just;
  PBlock block;

 public:
  ParaProposal(Just just, PBlock block);
  ParaProposal();

  Just getJust();
  PBlock getBlock();

  void serialize(salticidae::DataStream &data) const;
  void unserialize(salticidae::DataStream &data);

  std::string prettyPrint();
  std::string toString();
};


#endif
