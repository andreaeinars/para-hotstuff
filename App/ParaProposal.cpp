#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <string>
#include <cstring>

#include "ParaProposal.h"


Just ParaProposal::getJust()   { return (this->just);  }
PBlock ParaProposal::getBlock() { return (this->block); }

void ParaProposal::serialize(salticidae::DataStream &data) const {
  data << this->just << this->block;
}


void ParaProposal::unserialize(salticidae::DataStream &data) {
  data >> this->just >> this->block;
}


ParaProposal::ParaProposal(Just just, PBlock block) {
  this->just=just;
  this->block=block;
}


ParaProposal::ParaProposal() {}


std::string ParaProposal::prettyPrint() {
  return ("PARAPROP[" + (this->just).prettyPrint() + "," + (this->block).prettyPrint() + "]");
}

std::string ParaProposal::toString() {
  return ((this->just).toString() + (this->block).toString());
}
